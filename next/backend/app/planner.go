package app

import (
	"context"
	"fmt"
	"io"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
)

// CheckPlanner computes a route for the demo garden and reports it to w, to
// check that this build (and machine) runs the C++ planner.
func CheckPlanner(ctx context.Context, w io.Writer) error {
	m := link.DemoMap()
	area := planner.Area{Perimeter: m.Perimeter, Exclusions: m.Exclusions}
	s := planner.Settings{
		Pattern: planner.PatternLines, LaneWidthM: 0.18, AngleRad: 0.5, DistanceToBorderM: 0.18,
		MowArea: true, BorderLaps: 1, ExclusionLaps: 1,
	}
	start := time.Now()
	route, err := planner.New().Route(ctx, area, s, geo.Point{X: 1, Y: 1})
	if err != nil {
		return fmt.Errorf("check planner: %w", err)
	}
	_, err = fmt.Fprintf(w, "planner %s: route through the demo garden with %d points in %v\n",
		planner.Version(), len(route), time.Since(start).Round(time.Millisecond))
	return err
}
