package testkit

import (
	"context"
	"sync"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
)

// RouteCall is one call of FakePlanner.Route.
type RouteCall struct {
	Area     planner.Area
	Settings planner.Settings
	Start    geo.Point
}

// FakePlanner stands in for planner.Native in tests without the C++ planner.
// By default Route drives from the start to every perimeter point and Way
// goes straight to the goal; set RouteFunc/WayFunc for other answers or
// errors. Block makes calls wait until the context ends. Safe for concurrent use.
type FakePlanner struct {
	mu        sync.Mutex
	RouteFunc func(area planner.Area, s planner.Settings, start geo.Point) ([]geo.Point, error)
	WayFunc   func(area planner.Area, start, goal geo.Point) ([]geo.Point, error)
	Block     bool
	routes    []RouteCall
}

// Route records the call and answers with RouteFunc.
func (f *FakePlanner) Route(ctx context.Context, area planner.Area, s planner.Settings, start geo.Point) ([]geo.Point, error) {
	f.mu.Lock()
	f.routes = append(f.routes, RouteCall{Area: area, Settings: s, Start: start})
	fn, block := f.RouteFunc, f.Block
	f.mu.Unlock()
	if block {
		<-ctx.Done()
		return nil, ctx.Err()
	}
	if fn != nil {
		return fn(area, s, start)
	}
	return append([]geo.Point{start}, area.Perimeter...), nil
}

// Way answers with WayFunc, or the straight line from start to goal.
func (f *FakePlanner) Way(ctx context.Context, area planner.Area, start, goal geo.Point) ([]geo.Point, error) {
	f.mu.Lock()
	fn, block := f.WayFunc, f.Block
	f.mu.Unlock()
	if block {
		<-ctx.Done()
		return nil, ctx.Err()
	}
	if fn != nil {
		return fn(area, start, goal)
	}
	return []geo.Point{start, goal}, nil
}

// Routes returns the Route calls so far.
func (f *FakePlanner) Routes() []RouteCall {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]RouteCall(nil), f.routes...)
}
