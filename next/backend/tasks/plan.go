// Package tasks turns a selection of the garden and mow parameters into a
// route (through the planner) and keeps the route that is planned next.
package tasks

import (
	"errors"
	"fmt"
	"math"
	"strings"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
)

// Mow patterns, as in planner.
const (
	PatternLines   = "lines"
	PatternSquares = "squares"
	PatternRings   = "rings"
)

// Parameters control how a part of the garden is mowed. They match the
// planner settings of the user settings, which are the defaults in the UI.
type Parameters struct {
	Pattern  string  `json:"pattern"`
	WidthM   float64 `json:"widthM"` // distance between lanes (cutting width)
	AngleDeg float64 `json:"angleDeg"`
	// DistanceToBorder in lane widths, kept free along the border before the lanes.
	DistanceToBorder int  `json:"distanceToBorder"`
	MowArea          bool `json:"mowArea"`
	BorderLaps       int  `json:"borderLaps"`
	// MowExclusions drives around each exclusion, as many laps as along the
	// border but at least one.
	MowExclusions bool `json:"mowExclusions"`
	BorderCCW     bool `json:"borderCcw"`
}

// ErrInvalid wraps every validation error.
var ErrInvalid = errors.New("invalid task")

// Validate checks the parameters like settings.Planner, and that there is
// something to mow.
func (p Parameters) Validate() error {
	var errs []string
	if p.Pattern != PatternLines && p.Pattern != PatternSquares && p.Pattern != PatternRings {
		errs = append(errs, fmt.Sprintf("pattern must be lines, squares or rings, got %q", p.Pattern))
	}
	if math.IsNaN(p.WidthM) || p.WidthM < 0.01 || p.WidthM > 1 {
		errs = append(errs, "widthM must be between 0.01 and 1")
	}
	if math.IsNaN(p.AngleDeg) || p.AngleDeg < 0 || p.AngleDeg > 360 {
		errs = append(errs, "angleDeg must be between 0 and 360")
	}
	if p.DistanceToBorder < 0 || p.DistanceToBorder > 10 {
		errs = append(errs, "distanceToBorder must be between 0 and 10")
	}
	if p.BorderLaps < 0 || p.BorderLaps > 10 {
		errs = append(errs, "borderLaps must be between 0 and 10")
	}
	if !p.MowArea && p.BorderLaps == 0 && !p.MowExclusions {
		errs = append(errs, "nothing to mow: enable the area, border laps or exclusions")
	}
	if len(errs) > 0 {
		return fmt.Errorf("%w: %s", ErrInvalid, strings.Join(errs, "; "))
	}
	return nil
}

// settings converts the parameters for the planner.
func (p Parameters) settings() planner.Settings {
	exclusionLaps := 0
	if p.MowExclusions {
		exclusionLaps = max(p.BorderLaps, 1)
	}
	return planner.Settings{
		Pattern:           planner.Pattern(p.Pattern),
		LaneWidthM:        p.WidthM,
		AngleRad:          p.AngleDeg * math.Pi / 180,
		DistanceToBorderM: float64(p.DistanceToBorder) * p.WidthM,
		MowArea:           p.MowArea,
		BorderLaps:        p.BorderLaps,
		BorderCCW:         p.BorderCCW,
		ExclusionLaps:     exclusionLaps,
		ExclusionsCCW:     p.BorderCCW,
	}
}

// validSelection checks a selection: none (the whole garden) or a polygon.
func validSelection(sel []geo.Point) error {
	if len(sel) == 0 {
		return nil
	}
	if len(sel) < 3 {
		return fmt.Errorf("%w: selection needs at least 3 points or none", ErrInvalid)
	}
	for _, p := range sel {
		if math.IsNaN(p.X) || math.IsNaN(p.Y) || math.Abs(p.X) > maps.MaxCoordM*2 || math.Abs(p.Y) > maps.MaxCoordM*2 {
			return fmt.Errorf("%w: selection has a point out of range", ErrInvalid)
		}
	}
	return nil
}

// area is what the planner needs from the map and the selection.
func area(m maps.Map, sel []geo.Point) planner.Area {
	a := planner.Area{Perimeter: m.Perimeter, Exclusions: m.Exclusions, SearchWire: m.SearchWire}
	if len(sel) > 0 {
		a.MowAreas = [][]geo.Point{sel}
	}
	return a
}

// inStationM: a robot this close to the station leaves along the dock path,
// even if it does not charge (contacts, simulator).
const inStationM = 1.0

// startPoint is where the route begins, as in legacy CaSSAndRA: a docked
// robot leaves the station at the start of the dock path; a robot outside
// the perimeter starts at the nearest perimeter corner.
func startPoint(m maps.Map, pos geo.Point, docked bool) geo.Point {
	if n := len(m.Dock); n > 0 && (docked || dist(pos, m.Dock[n-1]) < inStationM) {
		pos = m.Dock[0]
	}
	if inside(m.Perimeter, pos) || len(m.Perimeter) == 0 {
		return pos
	}
	best := m.Perimeter[0]
	for _, p := range m.Perimeter[1:] {
		if dist(p, pos) < dist(best, pos) {
			best = p
		}
	}
	return best
}

// inside reports whether p lies in the polygon or on its border.
func inside(polygon []geo.Point, p geo.Point) bool {
	in := false
	for i, a := range polygon {
		b := polygon[(i+1)%len(polygon)]
		if onSegment(a, b, p) {
			return true
		}
		if (a.Y > p.Y) != (b.Y > p.Y) && p.X < (b.X-a.X)*(p.Y-a.Y)/(b.Y-a.Y)+a.X {
			in = !in
		}
	}
	return in
}

func onSegment(a, b, p geo.Point) bool {
	const eps = 1e-9
	cross := (b.X-a.X)*(p.Y-a.Y) - (b.Y-a.Y)*(p.X-a.X)
	if math.Abs(cross) > eps {
		return false
	}
	return p.X >= math.Min(a.X, b.X)-eps && p.X <= math.Max(a.X, b.X)+eps &&
		p.Y >= math.Min(a.Y, b.Y)-eps && p.Y <= math.Max(a.Y, b.Y)+eps
}

func dist(a, b geo.Point) float64 { return math.Hypot(a.X-b.X, a.Y-b.Y) }

// length is the distance along the route in meters.
func length(route []geo.Point) float64 {
	total := 0.0
	for i := 1; i < len(route); i++ {
		total += dist(route[i-1], route[i])
	}
	return total
}
