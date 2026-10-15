package maps

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strconv"
	"strings"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/jsonfile"
)

// legacyFrame is a pandas DataFrame saved with to_json() (orient
// "columns"): every column maps the row index ("0", "1", ...) to a value.
type legacyFrame struct {
	X    map[string]*float64 `json:"X"`
	Y    map[string]*float64 `json:"Y"`
	Type map[string]string   `json:"type"`
	Name map[string]string   `json:"name"`
}

// LegacyImport is the result of ImportLegacy.
type LegacyImport struct {
	Maps []Map // without ID, in the order of the legacy file
	// Active is the name of the map legacy CaSSAndRA had loaded ("" if none).
	Active   string
	Warnings []string
}

// ImportLegacy reads the maps of legacy CaSSAndRA from mapDir (the "map"
// folder of its data directory, e.g. ~/.cassandra/map): perimeter.json
// holds all maps, tmp.json the name of the loaded one. Maps that cannot be
// used are skipped with a warning. Without perimeter.json it returns an
// empty result.
func ImportLegacy(mapDir string) (LegacyImport, error) {
	var res LegacyImport
	var f legacyFrame
	if err := jsonfile.Read(filepath.Join(mapDir, "perimeter.json"), &f); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return res, nil
		}
		return res, fmt.Errorf("legacy maps: %w", err)
	}

	rows := make([]int, 0, len(f.Name))
	for key := range f.Name {
		i, err := strconv.Atoi(key)
		if err != nil {
			return res, fmt.Errorf("legacy maps: row %q is not a number", key)
		}
		rows = append(rows, i)
	}
	slices.Sort(rows)

	type parts struct {
		perimeter, dock, wire []geo.Point
		exclusions            map[int][]geo.Point
		problems              []string
	}
	var names []string
	byName := map[string]*parts{}
	for _, i := range rows {
		key := strconv.Itoa(i)
		name := f.Name[key]
		p := byName[name]
		if p == nil {
			p = &parts{exclusions: map[int][]geo.Point{}}
			byName[name] = p
			names = append(names, name)
		}
		x, y := f.X[key], f.Y[key]
		if x == nil || y == nil {
			p.problems = append(p.problems, fmt.Sprintf("row %d has no coordinates", i))
			continue
		}
		pt := geo.Point{X: *x, Y: *y}
		switch typ := f.Type[key]; {
		case typ == "perimeter":
			p.perimeter = append(p.perimeter, pt)
		case typ == "dockpoints":
			p.dock = append(p.dock, pt)
		case typ == "search wire":
			p.wire = append(p.wire, pt)
		case strings.HasPrefix(typ, "exclusion_"):
			n, err := strconv.Atoi(strings.TrimPrefix(typ, "exclusion_"))
			if err != nil {
				p.problems = append(p.problems, fmt.Sprintf("unknown type %q", typ))
				continue
			}
			p.exclusions[n] = append(p.exclusions[n], pt)
		default:
			p.problems = append(p.problems, fmt.Sprintf("unknown type %q", typ))
		}
	}

	for _, name := range names {
		p := byName[name]
		m := Map{Name: name, Perimeter: p.perimeter, Dock: p.dock, SearchWire: p.wire}
		nums := make([]int, 0, len(p.exclusions))
		for n := range p.exclusions {
			nums = append(nums, n)
		}
		slices.Sort(nums)
		for _, n := range nums {
			m.Exclusions = append(m.Exclusions, p.exclusions[n])
		}
		if len(p.problems) > 0 {
			res.Warnings = append(res.Warnings, fmt.Sprintf("map %q skipped: %s", name, strings.Join(p.problems, "; ")))
			continue
		}
		if err := m.Validate(); err != nil {
			res.Warnings = append(res.Warnings, fmt.Sprintf("map %q skipped: %v", name, err))
			continue
		}
		res.Maps = append(res.Maps, m.normalized())
	}

	var tmp struct {
		Name string `json:"PERIMETERNAME"`
	}
	if err := jsonfile.Read(filepath.Join(mapDir, "tmp.json"), &tmp); err != nil && !errors.Is(err, os.ErrNotExist) {
		res.Warnings = append(res.Warnings, fmt.Sprintf("active map: %v", err))
	}
	for _, m := range res.Maps {
		if m.Name == strings.TrimSpace(tmp.Name) {
			res.Active = m.Name
		}
	}
	return res, nil
}

// Import stores the maps of a legacy import and activates the legacy active
// map. Maps whose name is taken are skipped with a warning.
func (s *Store) Import(li LegacyImport) (imported int, warnings []string) {
	warnings = append(warnings, li.Warnings...)
	for _, m := range li.Maps {
		created, err := s.Create(m)
		if err != nil {
			warnings = append(warnings, fmt.Sprintf("map %q: %v", m.Name, err))
			continue
		}
		imported++
		if created.Name == li.Active {
			if err := s.SetActive(created.ID); err != nil {
				warnings = append(warnings, err.Error())
			}
		}
	}
	return imported, warnings
}
