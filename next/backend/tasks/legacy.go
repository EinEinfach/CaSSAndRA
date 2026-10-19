package tasks

import (
	"errors"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"slices"
	"strconv"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/jsonfile"
)

// legacyRows is tasks.json of legacy CaSSAndRA, a pandas DataFrame saved
// with to_json(): every column maps the row index to a value. Rows of one
// task share "map name" and "name"; "task nr" numbers its parts.
type legacyRows struct {
	X    map[string]*float64 `json:"X"`
	Y    map[string]*float64 `json:"Y"`
	Type map[string]string   `json:"type"`
	Map  map[string]string   `json:"map name"`
	Part map[string]int      `json:"task nr"`
	Name map[string]string   `json:"name"`
}

// legacyParameters is tasks_parameters.json: one row per part.
type legacyParameters struct {
	Map              map[string]string   `json:"map name"`
	Part             map[string]int      `json:"task nr"`
	Name             map[string]string   `json:"name"`
	Pattern          map[string]string   `json:"pattern"`
	Width            map[string]*float64 `json:"width"`
	Angle            map[string]*float64 `json:"angle"` // null = random in legacy
	DistanceToBorder map[string]*float64 `json:"distancetoborder"`
	MowArea          map[string]bool     `json:"mowarea"`
	MowBorder        map[string]*float64 `json:"mowborder"`
	MowExclusion     map[string]bool     `json:"mowexclusion"`
	MowBorderCCW     map[string]bool     `json:"mowborderccw"`
}

// LegacyImport is the result of ImportLegacy.
type LegacyImport struct {
	Tasks    []Task // without ID
	Warnings []string
}

type legacyKey struct {
	mapName, name string
}

// ImportLegacy reads the tasks of legacy CaSSAndRA from mapDir (tasks.json
// and tasks_parameters.json). mapIDs maps legacy map names to the IDs of the
// imported maps; tasks of other maps are skipped with a warning, as are
// tasks that cannot be used. The cached preview routes are not imported.
func ImportLegacy(mapDir string, mapIDs map[string]string) (LegacyImport, error) {
	var res LegacyImport
	var rows legacyRows
	var params legacyParameters
	if err := jsonfile.Read(filepath.Join(mapDir, "tasks.json"), &rows); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return res, nil
		}
		return res, fmt.Errorf("legacy tasks: %w", err)
	}
	if err := jsonfile.Read(filepath.Join(mapDir, "tasks_parameters.json"), &params); err != nil {
		return res, fmt.Errorf("legacy task parameters: %w", err)
	}

	type draft struct {
		lasso, rect map[int][]geo.Point
		params      map[int]Parameters
		problems    []string
	}
	var order []legacyKey
	drafts := map[legacyKey]*draft{}
	get := func(k legacyKey) *draft {
		d := drafts[k]
		if d == nil {
			d = &draft{lasso: map[int][]geo.Point{}, rect: map[int][]geo.Point{}, params: map[int]Parameters{}}
			drafts[k] = d
			order = append(order, k)
		}
		return d
	}

	for _, key := range sortedKeys(params.Name) {
		k := legacyKey{params.Map[key], params.Name[key]}
		d := get(k)
		p, err := params.row(key)
		if err != nil {
			d.problems = append(d.problems, err.Error())
			continue
		}
		d.params[params.Part[key]] = p
	}
	for _, key := range sortedKeys(rows.Name) {
		typ := rows.Type[key]
		if typ != "lassoPoints" && typ != "range" {
			continue // "preview route", "start position": computed anew
		}
		d := get(legacyKey{rows.Map[key], rows.Name[key]})
		x, y := rows.X[key], rows.Y[key]
		if x == nil || y == nil {
			d.problems = append(d.problems, "a selection point has no coordinates")
			continue
		}
		pt := geo.Point{X: *x, Y: *y}
		part := rows.Part[key]
		if typ == "range" {
			d.rect[part] = append(d.rect[part], pt)
		} else {
			d.lasso[part] = append(d.lasso[part], pt)
		}
	}

	for _, k := range order {
		d := drafts[k]
		mapID, ok := mapIDs[k.mapName]
		if !ok {
			res.Warnings = append(res.Warnings, fmt.Sprintf("task %q skipped: map %q was not imported", k.name, k.mapName))
			continue
		}
		t := Task{Name: k.name, MapID: mapID}
		nums := make([]int, 0, len(d.params))
		for n := range d.params {
			nums = append(nums, n)
		}
		slices.Sort(nums)
		for _, n := range nums {
			part := Part{Parameters: d.params[n]}
			switch rect := d.rect[n]; {
			case len(d.lasso[n]) > 0:
				part.Selection = d.lasso[n]
			case len(rect) == 2:
				part.Selection = rectangle(rect[0], rect[1])
			case len(rect) > 0:
				d.problems = append(d.problems, fmt.Sprintf("part %d: a rectangle needs 2 corners", n))
			}
			t.Parts = append(t.Parts, part)
		}
		if len(d.problems) == 0 {
			if err := t.Validate(); err != nil {
				d.problems = append(d.problems, err.Error())
			}
		}
		if len(d.problems) > 0 {
			res.Warnings = append(res.Warnings, fmt.Sprintf("task %q skipped: %v", k.name, d.problems))
			continue
		}
		res.Tasks = append(res.Tasks, t.normalized())
	}
	return res, nil
}

func (p legacyParameters) row(key string) (Parameters, error) {
	num := func(m map[string]*float64, name string) (float64, error) {
		v := m[key]
		if v == nil || math.IsNaN(*v) {
			return 0, fmt.Errorf("parameter %s missing", name)
		}
		return *v, nil
	}
	width, err := num(p.Width, "width")
	if err != nil {
		return Parameters{}, err
	}
	dist, err := num(p.DistanceToBorder, "distancetoborder")
	if err != nil {
		return Parameters{}, err
	}
	laps, err := num(p.MowBorder, "mowborder")
	if err != nil {
		return Parameters{}, err
	}
	angle := 0.0 // legacy picked a random angle for an empty one; a fixed one is predictable
	if v := p.Angle[key]; v != nil && !math.IsNaN(*v) {
		angle = math.Mod(math.Mod(*v, 360)+360, 360)
	}
	return Parameters{
		Pattern:          p.Pattern[key],
		WidthM:           width,
		AngleDeg:         angle,
		DistanceToBorder: int(math.Round(dist)),
		MowArea:          p.MowArea[key],
		BorderLaps:       int(math.Round(laps)),
		MowExclusions:    p.MowExclusion[key],
		BorderCCW:        p.MowBorderCCW[key],
	}, nil
}

// rectangle is the legacy "range" selection: two opposite corners.
func rectangle(a, c geo.Point) []geo.Point {
	x0, x1 := math.Min(a.X, c.X), math.Max(a.X, c.X)
	y0, y1 := math.Min(a.Y, c.Y), math.Max(a.Y, c.Y)
	return []geo.Point{{X: x0, Y: y0}, {X: x1, Y: y0}, {X: x1, Y: y1}, {X: x0, Y: y1}}
}

// sortedKeys returns the row indexes of a column in numeric order.
func sortedKeys[V any](column map[string]V) []string {
	keys := make([]string, 0, len(column))
	for k := range column {
		keys = append(keys, k)
	}
	slices.SortFunc(keys, func(a, b string) int {
		ia, _ := strconv.Atoi(a)
		ib, _ := strconv.Atoi(b)
		return ia - ib
	})
	return keys
}

// Import stores the tasks of a legacy import. Tasks that cannot be stored
// are skipped with a warning. Afterwards the file exists, even without
// tasks, so the import runs only once.
func (s *Store) Import(li LegacyImport) (imported int, warnings []string) {
	warnings = append(warnings, li.Warnings...)
	for _, t := range li.Tasks {
		if _, err := s.Create(t); err != nil {
			warnings = append(warnings, fmt.Sprintf("task %q: %v", t.Name, err))
			continue
		}
		imported++
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if !s.exists {
		if err := s.writeLocked(); err != nil {
			warnings = append(warnings, err.Error())
		}
	}
	return imported, warnings
}
