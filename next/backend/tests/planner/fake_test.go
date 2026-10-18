package planner_test

import (
	"context"
	"errors"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

// routePlanner is what features (tasks) will need; the fake must fit wherever
// the real planner does.
type routePlanner interface {
	Route(ctx context.Context, area planner.Area, s planner.Settings, start geo.Point) ([]geo.Point, error)
	Way(ctx context.Context, area planner.Area, start, goal geo.Point) ([]geo.Point, error)
}

var (
	_ routePlanner = (*planner.Native)(nil)
	_ routePlanner = (*testkit.FakePlanner)(nil)
)

func TestFakePlanner(t *testing.T) {
	ctx := context.Background()
	area := planner.Area{Perimeter: []geo.Point{{X: 0, Y: 0}, {X: 1, Y: 0}, {X: 1, Y: 1}}}
	start, goal := geo.Point{X: 0.5, Y: 0.2}, geo.Point{X: 0.9, Y: 0.1}
	f := &testkit.FakePlanner{}

	route, err := f.Route(ctx, area, planner.Settings{LaneWidthM: 0.2}, start)
	if err != nil || len(route) != 4 || route[0] != start {
		t.Errorf("default route = %v, %v", route, err)
	}
	if calls := f.Routes(); len(calls) != 1 || calls[0].Settings.LaneWidthM != 0.2 || calls[0].Start != start {
		t.Errorf("recorded calls = %+v", calls)
	}
	if way, err := f.Way(ctx, area, start, goal); err != nil || len(way) != 2 || way[1] != goal {
		t.Errorf("default way = %v, %v", way, err)
	}

	f.RouteFunc = func(planner.Area, planner.Settings, geo.Point) ([]geo.Point, error) { return nil, planner.ErrInvalid }
	f.WayFunc = func(planner.Area, geo.Point, geo.Point) ([]geo.Point, error) { return nil, planner.ErrNoPath }
	if _, err := f.Route(ctx, area, planner.Settings{}, start); !errors.Is(err, planner.ErrInvalid) {
		t.Errorf("RouteFunc error: %v", err)
	}
	if _, err := f.Way(ctx, area, start, goal); !errors.Is(err, planner.ErrNoPath) {
		t.Errorf("WayFunc error: %v", err)
	}

	f.Block = true
	cancelled, cancel := context.WithCancel(ctx)
	cancel()
	if _, err := f.Route(cancelled, area, planner.Settings{}, start); !errors.Is(err, context.Canceled) {
		t.Errorf("blocked route: %v", err)
	}
	if _, err := f.Way(cancelled, area, start, goal); !errors.Is(err, context.Canceled) {
		t.Errorf("blocked way: %v", err)
	}
}
