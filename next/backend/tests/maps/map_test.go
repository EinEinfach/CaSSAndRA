package maps_test

import (
	"errors"
	"math"
	"reflect"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

func TestValidate(t *testing.T) {
	tests := []struct {
		name   string
		change func(m *maps.Map)
		want   string // part of the error, "" = valid
	}{
		{"complete", func(*maps.Map) {}, ""},
		{"only a perimeter", func(m *maps.Map) { m.Exclusions, m.Dock, m.SearchWire = nil, nil, nil }, ""},
		{"no name", func(m *maps.Map) { m.Name = "  " }, "name"},
		{"long name", func(m *maps.Map) { m.Name = strings.Repeat("ä", 81) }, "name"},
		{"name of 80 umlauts", func(m *maps.Map) { m.Name = strings.Repeat("ä", 80) }, ""},
		{"perimeter too short", func(m *maps.Map) { m.Perimeter = pts(0, 0, 1, 1) }, "perimeter"},
		{"closed triangle is only 2 points", func(m *maps.Map) { m.Perimeter = pts(0, 0, 1, 0, 0, 0) }, "perimeter"},
		{"exclusion too short", func(m *maps.Map) { m.Exclusions = append(m.Exclusions, pts(1, 1)) }, "exclusion 2"},
		{"dock with one point", func(m *maps.Map) { m.Dock = pts(1, 1) }, "dock"},
		{"search wire with one point", func(m *maps.Map) { m.SearchWire = pts(1, 1) }, "search wire"},
		{"NaN", func(m *maps.Map) { m.Perimeter[1].X = math.NaN() }, "coordinates"},
		{"too far for the robot", func(m *maps.Map) { m.Dock[1].Y = 327.5 }, "coordinates"},
		{"exclusion too far", func(m *maps.Map) { m.Exclusions[0][0].X = -400 }, "coordinates"},
		{"wire too far", func(m *maps.Map) { m.SearchWire[0].X = math.Inf(1) }, "coordinates"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			m := garden("Garden")
			tt.change(&m)
			err := m.Validate()
			if tt.want == "" {
				if err != nil {
					t.Errorf("unexpected error: %v", err)
				}
				return
			}
			if !errors.Is(err, maps.ErrInvalid) || !strings.Contains(err.Error(), tt.want) {
				t.Errorf("err = %v, want ErrInvalid mentioning %q", err, tt.want)
			}
		})
	}
}

func TestRobotMap(t *testing.T) {
	m := garden("Garden")
	way := pts(5, 5, 6, 6)
	got := m.Robot(way)
	want := protocol.Map{Perimeter: m.Perimeter, Exclusions: m.Exclusions, Dock: m.Dock, Way: way}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("got %+v, want %+v (no search wire)", got, want)
	}
}

func TestCreateNormalizes(t *testing.T) {
	f := newStore(t)
	m := maps.Map{
		Name:       "  Closed  ",
		Perimeter:  pts(0, 0, 10, 0, 10, 10, 0, 0), // repeats the first point
		Exclusions: [][]geo.Point{pts(2, 2, 3, 2, 3, 3, 2, 2)},
	}
	got, err := f.store.Create(m)
	if err != nil {
		t.Fatal(err)
	}
	if got.Name != "Closed" || len(got.Perimeter) != 3 || len(got.Exclusions[0]) != 3 {
		t.Errorf("got %+v, want trimmed name and open polygons", got)
	}
	if got.Dock == nil || got.SearchWire == nil {
		t.Error("empty lists must not be nil (JSON null)")
	}
}
