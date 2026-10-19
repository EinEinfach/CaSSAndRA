//go:build cpp

package planner_test

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
)

// garden.json and golden.json: golden.json comes from the planner's Python
// module (make_golden.py), an independent way into the same C++ core.
type gardenFile struct {
	Perimeter  [][2]float64   `json:"perimeter"`
	Exclusions [][][2]float64 `json:"exclusions"`
	SearchWire [][2]float64   `json:"searchWire"`
	Routes     []struct {
		Name     string         `json:"name"`
		MowAreas [][][2]float64 `json:"mowAreas"`
		Settings struct {
			Pattern           planner.Pattern `json:"pattern"`
			LaneWidthM        float64         `json:"laneWidthM"`
			AngleRad          float64         `json:"angleRad"`
			DistanceToBorderM float64         `json:"distanceToBorderM"`
			MowArea           bool            `json:"mowArea"`
			BorderLaps        int             `json:"borderLaps"`
			BorderCCW         bool            `json:"borderCcw"`
			ExclusionLaps     int             `json:"exclusionLaps"`
			ExclusionsCCW     bool            `json:"exclusionsCcw"`
		} `json:"settings"`
		Start [2]float64 `json:"start"`
	} `json:"routes"`
}

type goldenFile struct {
	Version string `json:"version"`
	Routes  []struct {
		Name string       `json:"name"`
		Path [][2]float64 `json:"path"`
	} `json:"routes"`
}

func readJSON(t *testing.T, path string, v any) {
	t.Helper()
	b, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(b, v); err != nil {
		t.Fatal(err)
	}
}

func points(pts [][2]float64) []geo.Point {
	out := make([]geo.Point, len(pts))
	for i, p := range pts {
		out[i] = geo.Point{X: p[0], Y: p[1]}
	}
	return out
}

func polygons(polys [][][2]float64) [][]geo.Point {
	out := make([][]geo.Point, len(polys))
	for i, p := range polys {
		out[i] = points(p)
	}
	return out
}

func TestRoutesMatchThePythonModule(t *testing.T) {
	var garden gardenFile
	var golden goldenFile
	readJSON(t, "testdata/garden.json", &garden)
	readJSON(t, "testdata/golden.json", &golden)
	if golden.Version != planner.Version() {
		t.Fatalf("golden.json is from planner %s, linked is %s: run make_golden.py", golden.Version, planner.Version())
	}
	p := planner.New()
	for i, r := range garden.Routes {
		t.Run(r.Name, func(t *testing.T) {
			area := planner.Area{
				Perimeter:  points(garden.Perimeter),
				Exclusions: polygons(garden.Exclusions),
				MowAreas:   polygons(r.MowAreas),
				SearchWire: points(garden.SearchWire),
			}
			s := planner.Settings(r.Settings)
			got, err := p.Route(context.Background(), area, s, geo.Point{X: r.Start[0], Y: r.Start[1]})
			if err != nil {
				t.Fatal(err)
			}
			want := points(golden.Routes[i].Path)
			if len(got) != len(want) {
				t.Fatalf("%d points, want %d", len(got), len(want))
			}
			for j := range want {
				// Same code, but built with other flags: allow rounding differences.
				if math.Abs(got[j].X-want[j].X) > 1e-6 || math.Abs(got[j].Y-want[j].Y) > 1e-6 {
					t.Fatalf("point %d = %v, want %v", j, got[j], want[j])
				}
			}
		})
	}
}

// A 10 x 10 garden with a 2 x 2 exclusion in the middle.
var square = planner.Area{
	Perimeter:  []geo.Point{{X: 0, Y: 0}, {X: 10, Y: 0}, {X: 10, Y: 10}, {X: 0, Y: 10}},
	Exclusions: [][]geo.Point{{{X: 4, Y: 4}, {X: 6, Y: 4}, {X: 6, Y: 6}, {X: 4, Y: 6}}},
}

var lanes = planner.Settings{Pattern: planner.PatternLines, LaneWidthM: 0.5, MowArea: true}

// crossesHole reports whether the segment a-b runs through the inside of the
// 4..6 square (sampled, enough for lanes 0.5 m apart).
func crossesHole(a, b geo.Point) bool {
	for i := 1; i < 50; i++ {
		f := float64(i) / 50
		x, y := a.X+(b.X-a.X)*f, a.Y+(b.Y-a.Y)*f
		if x > 4+1e-6 && x < 6-1e-6 && y > 4+1e-6 && y < 6-1e-6 {
			return true
		}
	}
	return false
}

func TestRouteStaysInTheGardenAndOutOfExclusions(t *testing.T) {
	got, err := planner.New().Route(context.Background(), square, lanes, geo.Point{X: 0.5, Y: 0.5})
	if err != nil {
		t.Fatal(err)
	}
	if len(got) < 20 {
		t.Fatalf("only %d points", len(got))
	}
	for i, p := range got {
		if p.X < -1e-6 || p.X > 10+1e-6 || p.Y < -1e-6 || p.Y > 10+1e-6 {
			t.Errorf("point %d %v outside the garden", i, p)
		}
		if i > 0 && crossesHole(got[i-1], p) {
			t.Errorf("segment %d %v-%v crosses the exclusion", i, got[i-1], p)
		}
	}
}

// A selection over the corner of the garden: only 0..3 x 0..3 lies inside.
var cornerSelection = [][]geo.Point{{{X: -5, Y: -5}, {X: 3, Y: -5}, {X: 3, Y: 3}, {X: -5, Y: 3}}}

func TestMowAreasAreCutToThePerimeter(t *testing.T) {
	for _, pattern := range []planner.Pattern{planner.PatternLines, planner.PatternSquares, planner.PatternRings} {
		for _, distance := range []float64{0, 0.5} {
			t.Run(fmt.Sprintf("%s distance %v", pattern, distance), func(t *testing.T) {
				a := square
				a.MowAreas = cornerSelection
				s := planner.Settings{Pattern: pattern, LaneWidthM: 0.25, DistanceToBorderM: distance, MowArea: true, BorderLaps: 1}
				got, err := planner.New().Route(context.Background(), a, s, geo.Point{X: 1, Y: 1})
				if err != nil {
					t.Fatal(err)
				}
				if len(got) < 10 {
					t.Fatalf("only %d points", len(got))
				}
				for i, p := range got {
					if p.X < -1e-6 || p.X > 3+1e-6 || p.Y < -1e-6 || p.Y > 3+1e-6 {
						t.Fatalf("point %d %v outside the selected part of the garden", i, p)
					}
				}
			})
		}
	}
}

func TestMowAreasOutsideThePerimeter(t *testing.T) {
	a := square
	a.MowAreas = [][]geo.Point{{{X: 20, Y: 20}, {X: 30, Y: 20}, {X: 30, Y: 30}}}
	_, err := planner.New().Route(context.Background(), a, lanes, geo.Point{X: 1, Y: 1})
	if !errors.Is(err, planner.ErrInvalid) || !strings.Contains(err.Error(), "outside the perimeter") {
		t.Errorf("err = %v, want ErrInvalid: outside the perimeter", err)
	}
}

func TestWayGoesAroundTheExclusion(t *testing.T) {
	start, goal := geo.Point{X: 1, Y: 5}, geo.Point{X: 9, Y: 5}
	got, err := planner.New().Way(context.Background(), square, start, goal)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) < 3 || got[0] != start || got[len(got)-1] != goal {
		t.Fatalf("way = %v, want from %v to %v with a detour", got, start, goal)
	}
	for i := 1; i < len(got); i++ {
		if crossesHole(got[i-1], got[i]) {
			t.Errorf("segment %v-%v crosses the exclusion", got[i-1], got[i])
		}
	}
}

func TestWayToAnUnreachableGoal(t *testing.T) {
	_, err := planner.New().Way(context.Background(), square, geo.Point{X: 1, Y: 1}, geo.Point{X: 20, Y: 20})
	if !errors.Is(err, planner.ErrNoPath) {
		t.Errorf("err = %v, want ErrNoPath", err)
	}
}

func TestInvalidInput(t *testing.T) {
	tests := []struct {
		name   string
		change func(a *planner.Area, s *planner.Settings)
		want   string
	}{
		{"perimeter of two points", func(a *planner.Area, _ *planner.Settings) { a.Perimeter = a.Perimeter[:2] }, "perimeter"},
		{"NaN in an exclusion", func(a *planner.Area, _ *planner.Settings) {
			a.Exclusions = [][]geo.Point{{{X: 1, Y: 1}, {X: math.NaN(), Y: 2}, {X: 2, Y: 1}}}
		}, "finite"},
		{"mow area of two points", func(a *planner.Area, _ *planner.Settings) {
			a.MowAreas = [][]geo.Point{{{X: 1, Y: 1}, {X: 2, Y: 2}}}
		}, "mow area"},
		{"search wire of one point", func(a *planner.Area, _ *planner.Settings) { a.SearchWire = []geo.Point{{X: 1, Y: 1}} }, "virtual wire"},
		{"zero lane width", func(_ *planner.Area, s *planner.Settings) { s.LaneWidthM = 0 }, "offset"},
		{"unknown pattern", func(_ *planner.Area, s *planner.Settings) { s.Pattern = "spiral" }, "pattern"},
		{"negative laps", func(_ *planner.Area, s *planner.Settings) { s.BorderLaps = -1 }, "laps"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			a, s := square, lanes
			a.Exclusions = append([][]geo.Point(nil), square.Exclusions...)
			tt.change(&a, &s)
			_, err := planner.New().Route(context.Background(), a, s, geo.Point{X: 1, Y: 1})
			if !errors.Is(err, planner.ErrInvalid) || !strings.Contains(err.Error(), tt.want) {
				t.Errorf("err = %v, want ErrInvalid mentioning %q", err, tt.want)
			}
		})
	}
}

func TestVersion(t *testing.T) {
	if !planner.Available() || planner.Version() != "1.4" {
		t.Errorf("Available() = %v, Version() = %q", planner.Available(), planner.Version())
	}
}

// busyGarden keeps the planner busy for a few hundred milliseconds: 60 x 60 m
// with 64 exclusions and 10 cm lanes.
func busyGarden() (planner.Area, planner.Settings) {
	a := planner.Area{Perimeter: []geo.Point{{X: 0, Y: 0}, {X: 60, Y: 0}, {X: 60, Y: 60}, {X: 0, Y: 60}}}
	for i := range 8 {
		for j := range 8 {
			x, y := 3+float64(i)*7, 3+float64(j)*7
			a.Exclusions = append(a.Exclusions, []geo.Point{{X: x, Y: y}, {X: x + 2, Y: y}, {X: x + 2, Y: y + 2}, {X: x, Y: y + 2}})
		}
	}
	s := lanes
	s.LaneWidthM = 0.1
	return a, s
}

func TestOneRequestAtATimeAndContextsGiveUp(t *testing.T) {
	p := planner.New()
	area, s := busyGarden()
	first := make(chan error, 1)
	go func() {
		_, err := p.Route(context.Background(), area, s, geo.Point{X: 1, Y: 1})
		first <- err
	}()
	time.Sleep(50 * time.Millisecond) // the first request takes the planner

	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	if _, err := p.Route(ctx, square, lanes, geo.Point{X: 1, Y: 1}); !errors.Is(err, context.DeadlineExceeded) {
		t.Errorf("second request while the first runs: %v, want DeadlineExceeded", err)
	}
	if err := <-first; err != nil {
		t.Fatalf("first request: %v", err)
	}
	// The planner is free again.
	if _, err := p.Route(context.Background(), square, lanes, geo.Point{X: 1, Y: 1}); err != nil {
		t.Errorf("after the first request: %v", err)
	}
}

func TestACancelledRequestReturnsAtOnce(t *testing.T) {
	p := planner.New()
	area, s := busyGarden()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Millisecond)
	defer cancel()
	started := time.Now()
	_, err := p.Route(ctx, area, s, geo.Point{X: 1, Y: 1})
	if !errors.Is(err, context.DeadlineExceeded) || time.Since(started) > 150*time.Millisecond {
		t.Errorf("err = %v after %v, want DeadlineExceeded right after the deadline", err, time.Since(started))
	}
}

func TestParallelCallersGetTheirOwnResults(t *testing.T) {
	p := planner.New()
	want, err := p.Route(context.Background(), square, lanes, geo.Point{X: 0.5, Y: 0.5})
	if err != nil {
		t.Fatal(err)
	}
	var wg sync.WaitGroup
	for range 8 {
		wg.Go(func() {
			got, err := p.Route(context.Background(), square, lanes, geo.Point{X: 0.5, Y: 0.5})
			if err != nil || len(got) != len(want) {
				t.Errorf("parallel route: %d points, %v; want %d", len(got), err, len(want))
			}
		})
	}
	wg.Wait()
}
