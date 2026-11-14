//go:build cpp

package planner_test

import (
	"errors"
	"math"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
)

func rect(x0, y0, x1, y1 float64) []geo.Point {
	return []geo.Point{{X: x0, Y: y0}, {X: x1, Y: y0}, {X: x1, Y: y1}, {X: x0, Y: y1}}
}

// ringArea is positive whatever the direction of the ring.
func ringArea(r []geo.Point) float64 {
	sum := 0.0
	for i, p := range r {
		q := r[(i+1)%len(r)]
		sum += p.X*q.Y - q.X*p.Y
	}
	return math.Abs(sum) / 2
}

// The expected areas are plain rectangle arithmetic, not taken from Clipper.
func TestReshape(t *testing.T) {
	lawn := planner.Area{Perimeter: rect(0, 0, 10, 10), Exclusions: [][]geo.Point{rect(4, 4, 6, 6)}}
	tests := []struct {
		name           string
		area           planner.Area
		figure         []geo.Point
		add            bool
		wantPerimeter  float64 // m²
		wantExclusions []float64
	}{
		{"add across the border", lawn, rect(8, 2, 14, 6), true, 100 + 4*4, []float64{4}},
		{"add inside changes nothing", lawn, rect(1, 1, 3, 3), true, 100, []float64{4}},
		{"add over an exclusion fills it", lawn, rect(3, 3, 7, 7), true, 100, nil},
		{"add over half an exclusion", lawn, rect(5, 3, 7, 7), true, 100, []float64{2}},
		{"first figure becomes the perimeter", planner.Area{}, rect(0, 0, 3, 2), true, 6, nil},
		{"a figure drawn clockwise", planner.Area{}, []geo.Point{{X: 0, Y: 0}, {X: 0, Y: 2}, {X: 3, Y: 2}, {X: 3, Y: 0}}, true, 6, nil},
		{"subtract across the border", lawn, rect(8, 2, 14, 6), false, 100 - 2*4, []float64{4}},
		{"subtract inside makes an exclusion", lawn, rect(1, 1, 3, 3), false, 100, []float64{4, 4}},
		{"subtract next to an exclusion grows it", lawn, rect(6, 4, 8, 6), false, 100, []float64{8}},
		{"subtract from exclusion to border opens it", lawn, rect(5, 5, 12, 5.5), false, 100 - 4 - 4*0.5, nil},
	}
	p := planner.New()
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			perimeter, exclusions, err := p.Reshape(tt.area, tt.figure, tt.add)
			if err != nil {
				t.Fatal(err)
			}
			if got := ringArea(perimeter); math.Abs(got-tt.wantPerimeter) > 1e-6 {
				t.Errorf("perimeter area = %v, want %v (%v)", got, tt.wantPerimeter, perimeter)
			}
			if len(exclusions) != len(tt.wantExclusions) {
				t.Fatalf("exclusions = %v, want %d", exclusions, len(tt.wantExclusions))
			}
			if exclusions == nil {
				t.Error("exclusions are nil, want an empty list")
			}
			for i, e := range exclusions {
				found := false
				for _, want := range tt.wantExclusions {
					found = found || math.Abs(ringArea(e)-want) < 1e-6
				}
				if !found {
					t.Errorf("exclusion %d has area %v, want one of %v", i, ringArea(e), tt.wantExclusions)
				}
			}
		})
	}
}

func TestReshapeKeepsTheLawnInOnePiece(t *testing.T) {
	lawn := planner.Area{Perimeter: rect(0, 0, 10, 10)}
	tests := []struct {
		name   string
		area   planner.Area
		figure []geo.Point
		add    bool
	}{
		{"added next to the lawn", lawn, rect(12, 0, 14, 2), true},
		{"cut in two", lawn, rect(4, -1, 6, 11), false},
		{"everything cut away", lawn, rect(-1, -1, 11, 11), false},
		{"cut from nothing", planner.Area{}, rect(0, 0, 2, 2), false},
		{"figure of two points", lawn, []geo.Point{{X: 1, Y: 1}, {X: 2, Y: 2}}, true},
		{"figure without area", lawn, []geo.Point{{X: 1, Y: 1}, {X: 2, Y: 2}, {X: 3, Y: 3}}, false},
		{"broken perimeter", planner.Area{Perimeter: rect(0, 0, 1, 1)[:2]}, rect(0, 0, 2, 2), true},
	}
	p := planner.New()
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			perimeter, _, err := p.Reshape(tt.area, tt.figure, tt.add)
			if !errors.Is(err, planner.ErrInvalid) {
				t.Errorf("err = %v (perimeter %v), want ErrInvalid", err, perimeter)
			}
		})
	}
}

func TestReshapeRoundsToCentimeters(t *testing.T) {
	perimeter, _, err := planner.New().Reshape(planner.Area{Perimeter: rect(0, 0, 10, 10)}, rect(8.004, 2.006, 14.333, 6), true)
	if err != nil {
		t.Fatal(err)
	}
	for _, p := range perimeter {
		if math.Abs(p.X*100-math.Round(p.X*100)) > 1e-9 || math.Abs(p.Y*100-math.Round(p.Y*100)) > 1e-9 {
			t.Errorf("point %v is not in centimeters", p)
		}
	}
}
