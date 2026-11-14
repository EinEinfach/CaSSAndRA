package maps_test

import (
	"errors"
	"fmt"
	"net/http"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
)

// fakeReshaper records the call and answers with a fixed lawn or error.
type fakeReshaper struct {
	area   planner.Area
	figure []geo.Point
	add    bool
	err    error
}

func (f *fakeReshaper) Reshape(area planner.Area, figure []geo.Point, add bool) ([]geo.Point, [][]geo.Point, error) {
	f.area, f.figure, f.add = area, figure, add
	if f.err != nil {
		return nil, nil, f.err
	}
	return []geo.Point{{X: 0, Y: 0}, {X: 5, Y: 0}, {X: 5, Y: 5}}, nil, nil
}

const reshapeBody = `{"perimeter":[{"x":0,"y":0},{"x":4,"y":0},{"x":4,"y":4}],"exclusions":[],
	"figure":[{"x":3,"y":0},{"x":5,"y":0},{"x":5,"y":5}],"op":"%s"}`

func TestAPIReshape(t *testing.T) {
	f := newStore(t)
	for op, add := range map[string]bool{"add": true, "subtract": false} {
		shaper := &fakeReshaper{}
		rec := call(t, f.store.Handler(&fakeUploader{}, shaper), http.MethodPost, "/api/maps/reshape", fmt.Sprintf(reshapeBody, op))
		if rec.Code != http.StatusOK {
			t.Fatalf("%s: status %d (%s)", op, rec.Code, rec.Body)
		}
		// Lists are never null, also without exclusions.
		want := `{"perimeter":[{"x":0,"y":0},{"x":5,"y":0},{"x":5,"y":5}],"exclusions":[]}` + "\n"
		if rec.Body.String() != want {
			t.Errorf("%s: body = %s, want %s", op, rec.Body, want)
		}
		if shaper.add != add || len(shaper.area.Perimeter) != 3 || len(shaper.figure) != 3 {
			t.Errorf("%s: reshaper got add=%v area=%+v figure=%v", op, shaper.add, shaper.area, shaper.figure)
		}
	}
	if n := len(f.store.List()); n != 0 {
		t.Errorf("reshaping saved %d maps, want none", n)
	}
}

func TestAPIReshapeErrors(t *testing.T) {
	tests := []struct {
		name string
		body string
		err  error
		want int
	}{
		{"unknown op", fmt.Sprintf(reshapeBody, "xor"), nil, http.StatusBadRequest},
		{"broken body", `{"figure":`, nil, http.StatusBadRequest},
		{"lawn in pieces", fmt.Sprintf(reshapeBody, "subtract"), fmt.Errorf("%w: two pieces", planner.ErrInvalid), http.StatusBadRequest},
		{"built without planner", fmt.Sprintf(reshapeBody, "add"), planner.ErrUnavailable, http.StatusNotImplemented},
		{"clipper failed", fmt.Sprintf(reshapeBody, "add"), errors.New("boom"), http.StatusInternalServerError},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newStore(t)
			rec := call(t, f.store.Handler(&fakeUploader{}, &fakeReshaper{err: tt.err}), http.MethodPost, "/api/maps/reshape", tt.body)
			if rec.Code != tt.want {
				t.Errorf("status = %d, want %d (%s)", rec.Code, tt.want, rec.Body)
			}
		})
	}
}
