package tasks_test

import (
	"context"
	"errors"
	"net/http"
	"slices"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

// planned has a preview of the whole garden, computed with the robot at (5, 2).
func planned(t *testing.T) *fixture {
	t.Helper()
	f := newFixture(t)
	if _, err := f.svc.Preview(context.Background(), one(nil, params)); err != nil {
		t.Fatal(err)
	}
	return f
}

func TestStartSendsMapAndRouteThenMows(t *testing.T) {
	f := planned(t)
	if err := f.svc.Start(context.Background()); err != nil {
		t.Fatal(err)
	}
	calls, uploads := f.robot.sent()
	if !slices.Equal(calls, []string{"upload", "mow"}) {
		t.Fatalf("calls = %v, want upload, mow", calls)
	}
	m := uploads[0]
	plan := f.svc.Current()
	if !slices.Equal(m.Way, plan.Route) || !slices.Equal(m.Perimeter, garden.Perimeter) ||
		!slices.Equal(m.Dock, garden.Dock) || len(m.Exclusions) != 1 {
		t.Errorf("uploaded map = %+v, want the garden with the planned route", m)
	}
	if plan == nil {
		t.Error("the plan is gone after starting; it stays for the next start")
	}
}

func TestStartRefusesWhatNoLongerFits(t *testing.T) {
	tests := []struct {
		name   string
		change func(t *testing.T, f *fixture)
		want   error
	}{
		{"no plan", func(_ *testing.T, f *fixture) { f.svc.Clear() }, tasks.ErrNoPlan},
		{"the robot was driven away", func(_ *testing.T, f *fixture) {
			f.robot.set(geo.Point{X: 5, Y: 3.5}, protocol.OpIdle)
		}, tasks.ErrStalePlan},
		{"the map was edited (without MapsChanged)", func(t *testing.T, f *fixture) {
			m, _ := f.maps.Get(f.mapID)
			f.clock.Advance(time.Minute)
			if _, err := f.maps.Update(m); err != nil {
				t.Fatal(err)
			}
		}, tasks.ErrStalePlan},
		{"another map is active", func(t *testing.T, f *fixture) {
			other := garden
			other.Name = "other"
			o, err := f.maps.Create(other)
			if err != nil {
				t.Fatal(err)
			}
			if err := f.maps.SetActive(o.ID); err != nil {
				t.Fatal(err)
			}
		}, tasks.ErrStalePlan},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := planned(t)
			tt.change(t, f)
			if err := f.svc.Start(context.Background()); !errors.Is(err, tt.want) {
				t.Errorf("err = %v, want %v", err, tt.want)
			}
			if calls, _ := f.robot.sent(); len(calls) != 0 {
				t.Errorf("sent %v to the robot", calls)
			}
		})
	}
}

func TestStartAcceptsSmallMoves(t *testing.T) {
	f := planned(t)
	f.robot.set(geo.Point{X: 5.5, Y: 2.5}, protocol.OpIdle) // GPS jitter, a nudge
	if err := f.svc.Start(context.Background()); err != nil {
		t.Errorf("err = %v", err)
	}
}

func TestStartDoesNotMowWhenTheUploadFails(t *testing.T) {
	f := planned(t)
	f.robot.uploadErr = robot.ErrBusy
	err := f.svc.Start(context.Background())
	if !errors.Is(err, robot.ErrBusy) {
		t.Errorf("err = %v, want ErrBusy", err)
	}
	if calls, _ := f.robot.sent(); !slices.Equal(calls, []string{"upload"}) {
		t.Errorf("calls = %v, want only the upload", calls)
	}
}

func TestStartIsNeverRepeated(t *testing.T) {
	f := planned(t)
	f.robot.mowErr = link.ErrOffline
	if err := f.svc.Start(context.Background()); !errors.Is(err, link.ErrOffline) {
		t.Errorf("err = %v, want ErrOffline", err)
	}
	if calls, _ := f.robot.sent(); !slices.Equal(calls, []string{"upload", "mow"}) {
		t.Errorf("calls = %v, want one upload and one mow", calls)
	}
}

func TestASecondStartIsRefusedWhileTheFirstRuns(t *testing.T) {
	f := planned(t)
	f.robot.uploading, f.robot.release = make(chan struct{}), make(chan struct{})
	first := make(chan error, 1)
	go func() { first <- f.svc.Start(context.Background()) }()
	<-f.robot.uploading

	if err := f.svc.Start(context.Background()); !errors.Is(err, tasks.ErrStarting) {
		t.Errorf("second start: err = %v, want ErrStarting", err)
	}
	close(f.robot.release)
	if err := <-first; err != nil {
		t.Fatal(err)
	}
	if calls, _ := f.robot.sent(); !slices.Equal(calls, []string{"upload", "mow"}) {
		t.Errorf("calls = %v", calls)
	}
}

func TestAPIStart(t *testing.T) {
	tests := []struct {
		name  string
		setup func(f *fixture)
		want  int
	}{
		{"started", func(*fixture) {}, http.StatusNoContent},
		{"no plan", func(f *fixture) { f.svc.Clear() }, http.StatusConflict},
		{"robot moved", func(f *fixture) { f.robot.set(geo.Point{X: 9, Y: 9}, protocol.OpIdle) }, http.StatusConflict},
		{"robot driving", func(f *fixture) { f.robot.uploadErr = robot.ErrBusy }, http.StatusConflict},
		{"robot offline", func(f *fixture) { f.robot.mowErr = link.ErrOffline }, http.StatusServiceUnavailable},
		{"robot too slow", func(f *fixture) { f.robot.uploadErr = context.DeadlineExceeded }, http.StatusGatewayTimeout},
		{"checksum wrong", func(f *fixture) { f.robot.uploadErr = robot.ErrMapCRCMismatch }, http.StatusBadGateway},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := planned(t)
			tt.setup(f)
			req := httptestRequest("POST", "/api/tasks/start")
			rec := serve(f.svc.Handler(), req)
			if rec.Code != tt.want {
				t.Errorf("status = %d, want %d (%s)", rec.Code, tt.want, rec.Body)
			}
		})
	}
}

func TestPlanAndStartMowsItsOwnRoute(t *testing.T) {
	f := newFixture(t)
	f.planner.RouteFunc = func(area planner.Area, _ planner.Settings, start geo.Point) ([]geo.Point, error) {
		if len(area.MowAreas) > 0 {
			return append([]geo.Point{start}, area.MowAreas[0]...), nil
		}
		return append([]geo.Point{start}, area.Perimeter...), nil
	}
	f.robot.uploading, f.robot.release = make(chan struct{}), make(chan struct{})
	done := make(chan error, 1)
	var plan tasks.Plan
	go func() {
		var err error
		plan, err = f.svc.PlanAndStart(context.Background(), one(nil, params))
		done <- err
	}()
	<-f.robot.uploading
	// Someone previews another route while the first one is being sent.
	other, err := f.svc.Preview(context.Background(), one([]geo.Point{{X: 1, Y: 1}, {X: 3, Y: 1}, {X: 3, Y: 3}, {X: 1, Y: 3}}, params))
	if err != nil {
		t.Fatal(err)
	}
	close(f.robot.release)
	if err := <-done; err != nil {
		t.Fatal(err)
	}
	calls, uploads := f.robot.sent()
	if slices.Equal(other.Route, plan.Route) {
		t.Fatal("both previews have the same route; the test proves nothing")
	}
	if !slices.Equal(calls, []string{"upload", "mow"}) || !slices.Equal(uploads[0].Way, plan.Route) {
		t.Errorf("calls = %v, want the route of PlanAndStart uploaded once, then mow", calls)
	}
}

func TestPlanAndStartSendsNothingWhenPlanningFails(t *testing.T) {
	f := newFixture(t)
	_, err := f.svc.PlanAndStart(context.Background(), tasks.Request{TaskIDs: []string{"missing"}})
	if !errors.Is(err, tasks.ErrNotFound) {
		t.Errorf("err = %v, want ErrNotFound", err)
	}
	if calls, _ := f.robot.sent(); len(calls) != 0 {
		t.Errorf("sent %v", calls)
	}
}
