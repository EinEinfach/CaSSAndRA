package mqttapi

import (
	"context"
	"encoding/json"
	"fmt"
	"hash/fnv"
	"math"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

// Maps is what the API needs from the map store.
type Maps interface {
	ActiveID() string
	Get(id string) (maps.Map, error)
	List() []maps.Map
	Create(m maps.Map) (maps.Map, error)
	Update(m maps.Map) (maps.Map, error)
	Delete(id string) error
	SetActive(id string) error
}

// MapJSON is the payload of <prefix>/map (legacy maptopic.py). The ids
// change whenever the matching coordinates change; the native app then asks
// for them with {"coords": {"command": "update", "value": [...]}}.
type MapJSON struct {
	MapID                      string `json:"mapId"`
	PreviewID                  string `json:"previewId"`
	MowPathID                  string `json:"mowPathId"`
	ObstaclesID                string `json:"obstaclesId"`
	MowprogressIdxPercent      int    `json:"mowprogressIdxPercent"`
	MowprogressDistancePercent int    `json:"mowprogressDistancePercent"`
	FinishedDistance           int    `json:"finishedDistance"`
	DistanceTotal              int    `json:"distanceTotal"`
	FinishedIdx                int    `json:"finishedIdx"`
	IdxTotal                   int    `json:"idxTotal"`
	AreaTotal                  int    `json:"areaTotal"`
}

// MowParametersJSON is the payload of <prefix>/mowParameters and the value
// of {"map": {"command": "setMowParameters"}} (legacy names).
type MowParametersJSON struct {
	MowPattern         string `json:"mowPattern"`
	Width              Float  `json:"width"`
	Angle              int    `json:"angle"`
	DistanceToBorder   int    `json:"distanceToBorder"`
	MowArea            bool   `json:"mowArea"`
	BorderLaps         int    `json:"borderLaps"`
	MowExclusionBorder bool   `json:"mowExclusionBorder"`
	MowBorderCcw       bool   `json:"mowBorderCcw"`
}

func parametersJSON(p tasks.Parameters) MowParametersJSON {
	return MowParametersJSON{
		MowPattern: p.Pattern, Width: Float(p.WidthM), Angle: int(math.Round(p.AngleDeg)),
		DistanceToBorder: p.DistanceToBorder, MowArea: p.MowArea, BorderLaps: p.BorderLaps,
		MowExclusionBorder: p.MowExclusions, MowBorderCcw: p.BorderCCW,
	}
}

// fromParametersJSON takes the values legacy accepts and keeps the others,
// like legacy maptopic.py _setMowParameters.
func fromParametersJSON(raw json.RawMessage, cur tasks.Parameters) (tasks.Parameters, error) {
	var v struct {
		MowPattern         *string
		Width              *float64
		Angle              *float64
		DistanceToBorder   *float64
		MowArea            *bool
		BorderLaps         *float64
		MowExclusionBorder *bool
		MowBorderCcw       *bool
	}
	if err := json.Unmarshal(raw, &v); err != nil {
		return cur, fmt.Errorf("%w: mow parameters: %w", ErrInvalid, err)
	}
	p := cur
	if v.MowPattern != nil && (*v.MowPattern == "lines" || *v.MowPattern == "squares" || *v.MowPattern == "rings") {
		p.Pattern = *v.MowPattern
	}
	if v.Width != nil && *v.Width > 0.01 && *v.Width <= 1 {
		p.WidthM = *v.Width
	}
	if v.Angle != nil && *v.Angle >= 0 && *v.Angle <= 359 {
		p.AngleDeg = math.Trunc(*v.Angle)
	}
	if v.DistanceToBorder != nil && *v.DistanceToBorder >= 0 && *v.DistanceToBorder <= 5 {
		p.DistanceToBorder = int(*v.DistanceToBorder)
	}
	if v.MowArea != nil {
		p.MowArea = *v.MowArea
	}
	if v.BorderLaps != nil && *v.BorderLaps >= 0 && *v.BorderLaps <= 5 {
		p.BorderLaps = int(*v.BorderLaps)
	}
	if v.MowExclusionBorder != nil {
		p.MowExclusions = *v.MowExclusionBorder
	}
	if v.MowBorderCcw != nil {
		p.BorderCCW = *v.MowBorderCcw
	}
	return p, nil
}

// activeMap returns the active map, if any.
func (a *API) activeMap() (maps.Map, bool) {
	id := a.maps.ActiveID()
	if id == "" {
		return maps.Map{}, false
	}
	m, err := a.maps.Get(id)
	return m, err == nil
}

func mapID(m maps.Map, ok bool) string {
	if !ok {
		return ""
	}
	return fmt.Sprintf("%s-%d", m.ID, m.UpdatedAt.UnixMilli())
}

func previewID(p *tasks.Plan) string {
	if p == nil {
		return ""
	}
	return fmt.Sprintf("%s-%d", p.MapID, p.CreatedAt.UnixNano())
}

// pointsID is a short hash of the coordinates; "" without any.
func pointsID(lines ...[]geo.Point) string {
	h := fnv.New64a()
	n := 0
	for _, l := range lines {
		for _, p := range l {
			_, _ = fmt.Fprintf(h, "%.3f,%.3f;", p.X, p.Y)
			n++
		}
		_, _ = h.Write([]byte{'|'})
	}
	if n == 0 {
		return ""
	}
	return fmt.Sprintf("%016x", h.Sum64())
}

func (a *API) mapJSON() MapJSON {
	m, ok := a.activeMap()
	snap := a.robot.Snapshot()
	way := a.robot.Map().Way
	out := MapJSON{
		MapID:       mapID(m, ok),
		PreviewID:   previewID(a.tasks.Current()),
		MowPathID:   pointsID(way),
		ObstaclesID: pointsID(snap.Obstacles...),
		IdxTotal:    len(way),
		AreaTotal:   int(math.Round(a.area(m, ok))),
	}
	if len(way) > 0 {
		done := min(max(snap.MowPointIndex, 0), len(way))
		total, finished := length(way), length(way[:done])
		out.FinishedIdx = done
		out.DistanceTotal = int(math.Round(total))
		out.FinishedDistance = int(math.Round(finished))
		out.MowprogressIdxPercent = int(math.Round(float64(done) / float64(len(way)) * 100))
		if total > 0 {
			out.MowprogressDistancePercent = int(math.Round(finished / total * 100))
		}
	}
	return out
}

// area is the area of the current plan: its selections, or the lawn.
func (a *API) area(m maps.Map, ok bool) float64 {
	p := a.tasks.Current()
	if p == nil || !ok || p.MapID != m.ID {
		return 0
	}
	sum := 0.0
	for _, part := range p.Parts {
		if len(part.Selection) > 0 {
			sum += polygonArea(part.Selection)
			continue
		}
		sum += polygonArea(m.Perimeter)
		for _, e := range m.Exclusions {
			sum -= polygonArea(e)
		}
	}
	return sum
}

func polygonArea(pts []geo.Point) float64 {
	s := 0.0
	for i := range pts {
		j := (i + 1) % len(pts)
		s += pts[i].X*pts[j].Y - pts[j].X*pts[i].Y
	}
	return math.Abs(s) / 2
}

func length(pts []geo.Point) float64 {
	s := 0.0
	for i := 1; i < len(pts); i++ {
		s += math.Hypot(pts[i].X-pts[i-1].X, pts[i].Y-pts[i-1].Y)
	}
	return s
}

// mapCommand runs a command of the map topic.
func (a *API) mapCommand(c command) error {
	switch c.Command {
	case "setSelection":
		sel, err := c.points()
		if err != nil {
			return err
		}
		a.mu.Lock()
		a.selection = sel
		a.mu.Unlock()
		return nil
	case "setMowParameters":
		a.mu.Lock()
		defer a.mu.Unlock()
		p, err := fromParametersJSON(c.Value, a.parameters)
		if err != nil {
			return err
		}
		a.parameters = p
		return nil
	case "resetObstacles":
		a.robot.ClearObstacles()
		return nil
	case "resetRoute":
		a.tasks.Clear() // the route on the robot stays: it is the robot's
		return nil
	}
	return fmt.Errorf("%w: map command %q", ErrUnknown, c.Command)
}

// mowPlanned computes a route and starts it: the whole garden, the
// selection (both with the API's mow parameters) or the selected tasks.
func (a *API) mowPlanned(ctx context.Context, what string) error {
	a.mu.Lock()
	params, sel, ids := a.parameters, a.selection, a.selectedTasks
	a.mu.Unlock()
	var req tasks.Request
	switch what {
	case "all":
		req.Parts = []tasks.Part{{Parameters: params}}
	case "selection":
		if len(sel) < 3 {
			return fmt.Errorf("%w: no selection set (map setSelection)", ErrInvalid)
		}
		req.Parts = []tasks.Part{{Selection: sel, Parameters: params}}
	case "task":
		if len(ids) == 0 {
			return fmt.Errorf("%w: no tasks selected (tasks select)", ErrInvalid)
		}
		req.TaskIDs = ids
	default:
		return fmt.Errorf("%w: robot mow %q", ErrUnknown, what)
	}
	_, err := a.tasks.PlanAndStart(ctx, req)
	return err
}
