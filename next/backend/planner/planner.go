// Package planner computes mowing routes and ways between two points with the
// C++ PathPlannerCore (third_party/PathPlannerCore, through its C API). The
// C++ part is built only with the build tag cpp (cgo); without it, Native
// reports ErrUnavailable, so everything else builds and tests without a C++
// toolchain.
package planner

import (
	"context"
	"errors"
	"fmt"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
)

// Pattern is how the lanes cover the area.
type Pattern string

// Patterns of the planner.
const (
	PatternLines   Pattern = "lines"
	PatternSquares Pattern = "squares" // lines, then the same at 90°
	PatternRings   Pattern = "rings"   // concentric rings
)

// Area is where the robot may drive, in meters.
type Area struct {
	Perimeter  []geo.Point
	Exclusions [][]geo.Point
	// MowAreas are the parts to mow; none means the whole perimeter.
	MowAreas [][]geo.Point
	// SearchWire is a preferred way for transits (A*), may be empty.
	SearchWire []geo.Point
}

// Settings control the route.
type Settings struct {
	Pattern    Pattern
	LaneWidthM float64 // distance between lanes (cutting width)
	AngleRad   float64 // direction of the lanes
	// DistanceToBorderM is kept free along the border before the lanes start.
	DistanceToBorderM float64
	MowArea           bool // mow the area with lanes
	BorderLaps        int  // laps along the perimeter, 0 = none
	BorderCCW         bool
	ExclusionLaps     int // laps around each exclusion, 0 = none
	ExclusionsCCW     bool
}

// Errors of the planner; the returned errors wrap them with details.
var (
	// ErrUnavailable: built without the C++ planner (build tag cpp).
	ErrUnavailable = errors.New("path planner not available in this build")
	ErrInvalid     = errors.New("invalid planner input")
	ErrNoPath      = errors.New("no way to the goal")
	ErrFailed      = errors.New("path planner failed")
)

// Native is the C++ planner. It computes one request at a time, so a
// Raspberry Pi stays responsive; others wait (or give up with their context).
type Native struct {
	slot chan struct{}
}

// New returns the planner.
func New() *Native {
	return &Native{slot: make(chan struct{}, 1)}
}

// Available reports whether this build contains the C++ planner.
func Available() bool { return available }

// Version is the version of the C++ planner, "" without it.
func Version() string { return version() }

// Route computes the route that mows area with s, starting at start.
func (n *Native) Route(ctx context.Context, area Area, s Settings, start geo.Point) ([]geo.Point, error) {
	pts, err := n.run(ctx, func() ([]geo.Point, error) { return route(area, s, start) })
	if err != nil {
		return nil, fmt.Errorf("plan route: %w", err)
	}
	return pts, nil
}

// Way finds a way from start to goal inside the perimeter and around the
// exclusions, preferring the search wire. It starts at start and ends at goal.
func (n *Native) Way(ctx context.Context, area Area, start, goal geo.Point) ([]geo.Point, error) {
	pts, err := n.run(ctx, func() ([]geo.Point, error) { return way(area, start, goal) })
	if err != nil {
		return nil, fmt.Errorf("find way: %w", err)
	}
	return pts, nil
}

// run executes f in the planner slot. The C++ code cannot be interrupted: if
// ctx ends first, run returns and f finishes in the background.
func (n *Native) run(ctx context.Context, f func() ([]geo.Point, error)) ([]geo.Point, error) {
	if !available {
		return nil, ErrUnavailable
	}
	select {
	case n.slot <- struct{}{}:
	case <-ctx.Done():
		return nil, ctx.Err()
	}
	type result struct {
		pts []geo.Point
		err error
	}
	done := make(chan result, 1)
	go func() {
		defer func() { <-n.slot }()
		pts, err := f()
		done <- result{pts, err}
	}()
	select {
	case r := <-done:
		return r.pts, r.err
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}
