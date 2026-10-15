package maps_test

import (
	"fmt"
	"path/filepath"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

var t0 = time.Date(2026, 6, 1, 12, 0, 0, 0, time.UTC)

func pts(coords ...float64) []geo.Point {
	p := make([]geo.Point, len(coords)/2)
	for i := range p {
		p[i] = geo.Point{X: coords[2*i], Y: coords[2*i+1]}
	}
	return p
}

// garden is a valid map with every kind of element.
func garden(name string) maps.Map {
	return maps.Map{
		Name:       name,
		Perimeter:  pts(0, 0, 10, 0, 10, 10, 0, 10),
		Exclusions: [][]geo.Point{pts(2, 2, 3, 2, 3, 3)},
		Dock:       pts(1, 1, 1, 2),
		SearchWire: pts(0.5, 0.5, 5, 0.5),
	}
}

type storeFixture struct {
	store *maps.Store
	dir   string
	clock *testkit.FakeClock
}

// newStore opens a store in a temp dir with numbered IDs ("m1", "m2", ...).
func newStore(t *testing.T) storeFixture {
	t.Helper()
	dir := filepath.Join(t.TempDir(), "maps")
	clock := testkit.NewFakeClock(t0)
	return storeFixture{store: openStore(t, dir, clock), dir: dir, clock: clock}
}

func openStore(t *testing.T, dir string, clock *testkit.FakeClock) *maps.Store {
	t.Helper()
	n := 0
	s, err := maps.OpenStore(dir, maps.StoreConfig{
		NewID: func() string { n++; return fmt.Sprintf("m%d", n) },
		Now:   clock.Now,
	})
	if err != nil {
		t.Fatal(err)
	}
	return s
}
