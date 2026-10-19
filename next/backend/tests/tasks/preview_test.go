package tasks_test

import (
	"context"
	"errors"
	"math"
	"slices"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

func TestParametersValidate(t *testing.T) {
	tests := []struct {
		name   string
		change func(p *tasks.Parameters)
		want   string // "" = valid
	}{
		{"defaults", func(*tasks.Parameters) {}, ""},
		{"only the border", func(p *tasks.Parameters) { p.MowArea, p.MowExclusions = false, false }, ""},
		{"unknown pattern", func(p *tasks.Parameters) { p.Pattern = "spiral" }, "pattern"},
		{"lane too narrow", func(p *tasks.Parameters) { p.WidthM = 0.001 }, "widthM"},
		{"NaN lane", func(p *tasks.Parameters) { p.WidthM = math.NaN() }, "widthM"},
		{"angle over 360", func(p *tasks.Parameters) { p.AngleDeg = 361 }, "angleDeg"},
		{"negative distance", func(p *tasks.Parameters) { p.DistanceToBorder = -1 }, "distanceToBorder"},
		{"too many laps", func(p *tasks.Parameters) { p.BorderLaps = 11 }, "borderLaps"},
		{"nothing to mow", func(p *tasks.Parameters) { p.MowArea, p.BorderLaps, p.MowExclusions = false, 0, false }, "nothing to mow"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			p := params
			tt.change(&p)
			err := p.Validate()
			if tt.want == "" {
				if err != nil {
					t.Errorf("err = %v, want valid", err)
				}
				return
			}
			if !errors.Is(err, tasks.ErrInvalid) || !strings.Contains(err.Error(), tt.want) {
				t.Errorf("err = %v, want ErrInvalid mentioning %q", err, tt.want)
			}
		})
	}
}

func TestPreviewAsksThePlanner(t *testing.T) {
	f := newFixture(t)
	sel := []geo.Point{{X: 1, Y: 1}, {X: 3, Y: 1}, {X: 3, Y: 3}}
	plan, err := f.svc.Preview(context.Background(), one(sel, params))
	if err != nil {
		t.Fatal(err)
	}
	calls := f.planner.Routes()
	if len(calls) != 1 {
		t.Fatalf("%d planner calls, want 1", len(calls))
	}
	c := calls[0]
	if len(c.Area.Perimeter) != 4 || len(c.Area.Exclusions) != 1 || len(c.Area.SearchWire) != 2 {
		t.Errorf("area = %+v, want the garden with its exclusion and search wire", c.Area)
	}
	if len(c.Area.MowAreas) != 1 || len(c.Area.MowAreas[0]) != 3 {
		t.Errorf("mow areas = %v, want the selection", c.Area.MowAreas)
	}
	want := planner.Settings{
		Pattern: planner.PatternLines, LaneWidthM: 0.2, AngleRad: math.Pi / 2,
		DistanceToBorderM: 0.4, // 2 lane widths
		MowArea:           true, BorderLaps: 1, ExclusionLaps: 1,
	}
	if math.Abs(c.Settings.AngleRad-want.AngleRad) > 1e-12 || math.Abs(c.Settings.DistanceToBorderM-0.4) > 1e-12 {
		t.Errorf("settings = %+v, want %+v", c.Settings, want)
	}
	c.Settings.AngleRad, c.Settings.DistanceToBorderM = want.AngleRad, want.DistanceToBorderM
	if c.Settings != want {
		t.Errorf("settings = %+v, want %+v", c.Settings, want)
	}

	// The fake planner drives from the start to every perimeter corner.
	if plan.MapID != f.mapID || plan.Start != (geo.Point{X: 5, Y: 2}) || len(plan.Route) != 5 {
		t.Errorf("plan = %+v", plan)
	}
	if want := math.Hypot(5, 2) + 30; math.Abs(plan.DistanceM-want) > 1e-9 {
		t.Errorf("distance = %v, want %v", plan.DistanceM, want)
	}
	if !plan.CreatedAt.Equal(t0) || len(plan.Parts) != 1 || len(plan.Parts[0].Selection) != 3 || plan.Parts[0].Parameters != params {
		t.Errorf("plan = %+v", plan)
	}
	if cur := f.svc.Current(); cur == nil || len(cur.Route) != 5 {
		t.Errorf("current = %+v, want the plan", cur)
	}
}

func TestPreviewOfTheWholeGarden(t *testing.T) {
	f := newFixture(t)
	plan, err := f.svc.Preview(context.Background(), one(nil, params))
	if err != nil {
		t.Fatal(err)
	}
	if c := f.planner.Routes()[0]; c.Area.MowAreas != nil {
		t.Errorf("mow areas = %v, want none", c.Area.MowAreas)
	}
	if plan.Parts[0].Selection == nil || plan.TaskIDs == nil {
		t.Error("selection or task IDs nil, want [] for the JSON")
	}
}

func TestExclusionLapsFollowTheBorderLaps(t *testing.T) {
	tests := []struct {
		borderLaps    int
		mowExclusions bool
		want          int
	}{
		{0, true, 1},
		{3, true, 3},
		{3, false, 0},
	}
	for _, tt := range tests {
		f := newFixture(t)
		p := params
		p.BorderLaps, p.MowExclusions = tt.borderLaps, tt.mowExclusions
		if _, err := f.svc.Preview(context.Background(), one(nil, p)); err != nil {
			t.Fatal(err)
		}
		if got := f.planner.Routes()[0].Settings.ExclusionLaps; got != tt.want {
			t.Errorf("border laps %d, exclusions %v: exclusion laps = %d, want %d",
				tt.borderLaps, tt.mowExclusions, got, tt.want)
		}
	}
}

func TestRouteStartsWhereTheRobotLeavesFrom(t *testing.T) {
	tests := []struct {
		name string
		pos  geo.Point
		op   protocol.Op
		want geo.Point
	}{
		{"inside the garden", geo.Point{X: 5, Y: 2}, protocol.OpIdle, geo.Point{X: 5, Y: 2}},
		{"on the border", geo.Point{X: 10, Y: 3}, protocol.OpIdle, geo.Point{X: 10, Y: 3}},
		{"docked: start of the dock path", geo.Point{X: 2, Y: -1}, protocol.OpCharge, geo.Point{X: 2, Y: 1}},
		{"outside: nearest corner", geo.Point{X: 12, Y: 9}, protocol.OpIdle, geo.Point{X: 10, Y: 10}},
		{"in the station but not charging", geo.Point{X: 2.3, Y: -1.2}, protocol.OpIdle, geo.Point{X: 2, Y: 1}},
		{"outside, away from the station", geo.Point{X: 2, Y: -3}, protocol.OpIdle, geo.Point{X: 0, Y: 0}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			f.robot.set(tt.pos, tt.op)
			plan, err := f.svc.Preview(context.Background(), one(nil, params))
			if err != nil {
				t.Fatal(err)
			}
			if plan.Start != tt.want || f.planner.Routes()[0].Start != tt.want {
				t.Errorf("start = %v, want %v", plan.Start, tt.want)
			}
		})
	}
}

func TestPreviewErrors(t *testing.T) {
	tests := []struct {
		name  string
		setup func(f *fixture)
		req   tasks.Request
		want  error
	}{
		{"invalid parameters", nil, one(nil, tasks.Parameters{Pattern: "lines"}), tasks.ErrInvalid},
		{"selection of two points", nil, one([]geo.Point{{X: 1, Y: 1}, {X: 2, Y: 2}}, params), tasks.ErrInvalid},
		{"selection with NaN", nil, one([]geo.Point{{X: 1, Y: 1}, {X: math.NaN(), Y: 2}, {X: 2, Y: 1}}, params), tasks.ErrInvalid},
		{"no active map", func(f *fixture) { _ = f.maps.SetActive("") }, one(nil, params), tasks.ErrNoMap},
		{"planner unavailable", func(f *fixture) {
			f.planner.RouteFunc = func(planner.Area, planner.Settings, geo.Point) ([]geo.Point, error) {
				return nil, planner.ErrUnavailable
			}
		}, one(nil, params), planner.ErrUnavailable},
		{"empty route", func(f *fixture) {
			f.planner.RouteFunc = func(_ planner.Area, _ planner.Settings, start geo.Point) ([]geo.Point, error) {
				return []geo.Point{start}, nil
			}
		}, one(nil, params), tasks.ErrNothingToMow},
		{"selection outside the garden", func(f *fixture) {
			f.planner.RouteFunc = func(planner.Area, planner.Settings, geo.Point) ([]geo.Point, error) {
				return nil, planner.ErrInvalid
			}
		}, one([]geo.Point{{X: 20, Y: 20}, {X: 30, Y: 20}, {X: 30, Y: 30}}, params), tasks.ErrNothingToMow},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			if tt.setup != nil {
				tt.setup(f)
			}
			_, err := f.svc.Preview(context.Background(), tt.req)
			if !errors.Is(err, tt.want) {
				t.Errorf("err = %v, want %v", err, tt.want)
			}
			if f.svc.Current() != nil {
				t.Error("a failed preview became the plan")
			}
		})
	}
}

func TestTheLastRequestedPreviewStays(t *testing.T) {
	f := newFixture(t)
	release := map[float64]chan struct{}{0.2: make(chan struct{}), 0.3: make(chan struct{})}
	f.planner.RouteFunc = func(_ planner.Area, s planner.Settings, start geo.Point) ([]geo.Point, error) {
		<-release[s.LaneWidthM]
		return []geo.Point{start, {X: s.LaneWidthM, Y: 0}}, nil
	}
	preview := func(width float64) <-chan error {
		done := make(chan error, 1)
		p := params
		p.WidthM = width
		go func() {
			_, err := f.svc.Preview(context.Background(), one(nil, p))
			done <- err
		}()
		return done
	}
	first := preview(0.2)
	waitFor(t, func() bool { return len(f.planner.Routes()) == 1 })
	second := preview(0.3)
	waitFor(t, func() bool { return len(f.planner.Routes()) == 2 })

	close(release[0.3])
	if err := <-second; err != nil {
		t.Fatal(err)
	}
	close(release[0.2])
	if err := <-first; err != nil {
		t.Fatal(err)
	}
	if got := f.svc.Current().Parts[0].Parameters.WidthM; got != 0.3 {
		t.Errorf("plan has width %v, want 0.3 from the later request", got)
	}
}

func TestClearAndNotifications(t *testing.T) {
	f := newFixture(t)
	var mu sync.Mutex
	var got []*tasks.Plan
	f.svc.OnChange(func(p *tasks.Plan) {
		mu.Lock()
		defer mu.Unlock()
		got = append(got, p)
	})
	if _, err := f.svc.Preview(context.Background(), one(nil, params)); err != nil {
		t.Fatal(err)
	}
	f.svc.Clear()
	f.svc.Clear() // nothing to clear: no notification
	mu.Lock()
	defer mu.Unlock()
	if len(got) != 2 || got[0] == nil || got[1] != nil {
		t.Errorf("notifications = %v, want the plan, then nil", got)
	}
	if f.svc.Current() != nil {
		t.Error("plan still there after Clear")
	}
}

func TestPlanFollowsTheActiveMap(t *testing.T) {
	tests := []struct {
		name   string
		change func(t *testing.T, f *fixture)
		keep   bool
	}{
		{"another map is added", func(t *testing.T, f *fixture) {
			other := garden
			other.Name = "other"
			if _, err := f.maps.Create(other); err != nil {
				t.Fatal(err)
			}
		}, true},
		{"the map is edited", func(t *testing.T, f *fixture) {
			m, _ := f.maps.Get(f.mapID)
			m.Perimeter = append(m.Perimeter, geo.Point{X: -1, Y: 5})
			f.clock.Advance(time.Minute)
			if _, err := f.maps.Update(m); err != nil {
				t.Fatal(err)
			}
		}, false},
		{"no map is active", func(t *testing.T, f *fixture) {
			if err := f.maps.SetActive(""); err != nil {
				t.Fatal(err)
			}
		}, false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			f.maps.OnChange(f.svc.MapsChanged)
			if _, err := f.svc.Preview(context.Background(), one(nil, params)); err != nil {
				t.Fatal(err)
			}
			tt.change(t, f)
			if kept := f.svc.Current() != nil; kept != tt.keep {
				t.Errorf("plan kept = %v, want %v", kept, tt.keep)
			}
		})
	}
}

func waitFor(t *testing.T, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(2 * time.Second)
	for !cond() {
		if time.Now().After(deadline) {
			t.Fatal("condition not met in time")
		}
		time.Sleep(time.Millisecond)
	}
}

func TestPartsAreChainedEndToStart(t *testing.T) {
	f := newFixture(t)
	n := 0
	f.planner.RouteFunc = func(_ planner.Area, _ planner.Settings, start geo.Point) ([]geo.Point, error) {
		n++
		end := geo.Point{X: float64(n), Y: float64(n)}
		return []geo.Point{start, {X: 9, Y: float64(n)}, end}, nil
	}
	sel := []geo.Point{{X: 1, Y: 1}, {X: 3, Y: 1}, {X: 3, Y: 3}}
	req := tasks.Request{Parts: []tasks.Part{{Parameters: params}, {Selection: sel, Parameters: params}}}
	plan, err := f.svc.Preview(context.Background(), req)
	if err != nil {
		t.Fatal(err)
	}
	calls := f.planner.Routes()
	if len(calls) != 2 || calls[1].Start != (geo.Point{X: 1, Y: 1}) || len(calls[1].Area.MowAreas) != 1 {
		t.Fatalf("calls = %+v, want the second part to start at the end of the first", calls)
	}
	want := []geo.Point{{X: 5, Y: 2}, {X: 9, Y: 1}, {X: 1, Y: 1}, {X: 9, Y: 2}, {X: 2, Y: 2}}
	if !slices.Equal(plan.Route, want) {
		t.Errorf("route = %v, want %v (the joint point once)", plan.Route, want)
	}
	if len(plan.Parts) != 2 {
		t.Errorf("plan parts = %d, want 2", len(plan.Parts))
	}
}

func TestPreviewOfSavedTasksInTheGivenOrder(t *testing.T) {
	f := newFixture(t)
	wide := params
	wide.WidthM = 0.5
	a, err := f.tasks.Create(tasks.Task{Name: "A", MapID: f.mapID, Parts: []tasks.Part{{Parameters: params}, {Parameters: params}}})
	if err != nil {
		t.Fatal(err)
	}
	b, err := f.tasks.Create(tasks.Task{Name: "B", MapID: f.mapID, Parts: []tasks.Part{{Parameters: wide}}})
	if err != nil {
		t.Fatal(err)
	}
	plan, err := f.svc.Preview(context.Background(), tasks.Request{TaskIDs: []string{b.ID, a.ID}})
	if err != nil {
		t.Fatal(err)
	}
	calls := f.planner.Routes()
	if len(calls) != 3 || calls[0].Settings.LaneWidthM != 0.5 || calls[1].Settings.LaneWidthM != 0.2 {
		t.Errorf("calls = %+v, want B, then both parts of A", calls)
	}
	if !slices.Equal(plan.TaskIDs, []string{b.ID, a.ID}) || len(plan.Parts) != 3 {
		t.Errorf("plan tasks %v with %d parts", plan.TaskIDs, len(plan.Parts))
	}
}

func TestPreviewOfTasksRefuses(t *testing.T) {
	f := newFixture(t)
	other, err := f.tasks.Create(tasks.Task{Name: "Elsewhere", MapID: "another-map", Parts: []tasks.Part{{Parameters: params}}})
	if err != nil {
		t.Fatal(err)
	}
	mine, err := f.tasks.Create(tasks.Task{Name: "Mine", MapID: f.mapID, Parts: []tasks.Part{{Parameters: params}}})
	if err != nil {
		t.Fatal(err)
	}
	tests := []struct {
		name string
		req  tasks.Request
		want error
	}{
		{"unknown task", tasks.Request{TaskIDs: []string{"nope"}}, tasks.ErrNotFound},
		{"task of another map", tasks.Request{TaskIDs: []string{other.ID}}, tasks.ErrInvalid},
		{"tasks and parts", tasks.Request{TaskIDs: []string{mine.ID}, Parts: []tasks.Part{{Parameters: params}}}, tasks.ErrInvalid},
		{"nothing", tasks.Request{}, tasks.ErrInvalid},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if _, err := f.svc.Preview(context.Background(), tt.req); !errors.Is(err, tt.want) {
				t.Errorf("err = %v, want %v", err, tt.want)
			}
		})
	}
}
