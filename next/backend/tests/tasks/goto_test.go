package tasks_test

import (
	"context"
	"errors"
	"math"
	"net/http"
	"net/http/httptest"
	"slices"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

func TestGotoSendsTheWayThenDrives(t *testing.T) {
	f := newFixture(t)
	detour := []geo.Point{{X: 5, Y: 2}, {X: 7, Y: 3}, {X: 8, Y: 8}}
	var asked planner.Area
	f.planner.WayFunc = func(a planner.Area, start, goal geo.Point) ([]geo.Point, error) {
		asked = a
		if start != (geo.Point{X: 5, Y: 2}) || goal != (geo.Point{X: 8, Y: 8}) {
			t.Errorf("way from %v to %v", start, goal)
		}
		return detour, nil
	}
	way, err := f.svc.Goto(context.Background(), geo.Point{X: 8, Y: 8})
	if err != nil {
		t.Fatal(err)
	}
	if !slices.Equal(way, detour) {
		t.Errorf("way = %v", way)
	}
	if len(asked.Exclusions) != 1 || len(asked.SearchWire) != 2 || asked.MowAreas != nil {
		t.Errorf("area = %+v, want the map with exclusions and search wire", asked)
	}
	calls, uploads := f.robot.sent()
	if !slices.Equal(calls, []string{"upload", "goto"}) {
		t.Fatalf("calls = %v, want upload, goto", calls)
	}
	if !slices.Equal(uploads[0].Way, detour) || len(uploads[0].Dock) != 2 {
		t.Errorf("uploaded = %+v, want the map with dock path and the way", uploads[0])
	}
}

func TestGotoFromTheDockLeavesAlongTheDockPath(t *testing.T) {
	f := newFixture(t)
	f.robot.set(geo.Point{X: 2, Y: -1}, protocol.OpCharge)
	var from geo.Point
	f.planner.WayFunc = func(_ planner.Area, start, goal geo.Point) ([]geo.Point, error) {
		from = start
		return []geo.Point{start, goal}, nil
	}
	if _, err := f.svc.Goto(context.Background(), geo.Point{X: 8, Y: 8}); err != nil {
		t.Fatal(err)
	}
	if from != (geo.Point{X: 2, Y: 1}) {
		t.Errorf("way starts at %v, want the start of the dock path", from)
	}
}

func TestGotoRefuses(t *testing.T) {
	tests := []struct {
		name  string
		setup func(f *fixture)
		goal  geo.Point
		want  error
		sent  []string
	}{
		{"outside the garden", nil, geo.Point{X: 12, Y: 5}, tasks.ErrUnreachable, nil},
		{"inside an exclusion", nil, geo.Point{X: 5, Y: 5}, tasks.ErrUnreachable, nil},
		{"not a number", nil, geo.Point{X: math.NaN(), Y: 1}, tasks.ErrInvalid, nil},
		{"no way", func(f *fixture) {
			f.planner.WayFunc = func(planner.Area, geo.Point, geo.Point) ([]geo.Point, error) {
				return nil, planner.ErrNoPath
			}
		}, geo.Point{X: 8, Y: 8}, tasks.ErrUnreachable, nil},
		{"no active map", func(f *fixture) { _ = f.maps.SetActive("") }, geo.Point{X: 8, Y: 8}, tasks.ErrNoMap, nil},
		{"robot driving", func(f *fixture) { f.robot.uploadErr = robot.ErrBusy }, geo.Point{X: 8, Y: 8}, robot.ErrBusy, []string{"upload"}},
		{"robot offline", func(f *fixture) { f.robot.mowErr = link.ErrOffline }, geo.Point{X: 8, Y: 8}, link.ErrOffline, []string{"upload", "goto"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			if tt.setup != nil {
				tt.setup(f)
			}
			if _, err := f.svc.Goto(context.Background(), tt.goal); !errors.Is(err, tt.want) {
				t.Errorf("err = %v, want %v", err, tt.want)
			}
			if calls, _ := f.robot.sent(); !slices.Equal(calls, tt.sent) {
				t.Errorf("calls = %v, want %v (never repeated)", calls, tt.sent)
			}
		})
	}
}

func TestGotoOnTheBorderOfAnExclusion(t *testing.T) {
	f := newFixture(t)
	if _, err := f.svc.Goto(context.Background(), geo.Point{X: 4, Y: 5}); err != nil {
		t.Errorf("err = %v; the edge of an exclusion is lawn", err)
	}
}

func TestAPIGoto(t *testing.T) {
	tests := []struct {
		body string
		want int
	}{
		{`{"x":8,"y":8}`, http.StatusOK},
		{`{"x":8}`, http.StatusBadRequest},
		{`{"x":30,"y":8}`, http.StatusBadRequest},
		{`{`, http.StatusBadRequest},
	}
	for _, tt := range tests {
		f := newFixture(t)
		rec := serve(f.svc.Handler(), httptest.NewRequest("POST", "/api/tasks/goto", strings.NewReader(tt.body)))
		if rec.Code != tt.want {
			t.Errorf("%s: status %d, want %d (%s)", tt.body, rec.Code, tt.want, rec.Body)
		}
		if tt.want == http.StatusOK && !strings.Contains(rec.Body.String(), `"way":[{"x":5,"y":2},{"x":8,"y":8}]`) {
			t.Errorf("body = %s", rec.Body)
		}
	}
}
