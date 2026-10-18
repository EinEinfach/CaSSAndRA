//go:build !cpp

package planner_test

import (
	"context"
	"errors"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
)

// Without the build tag cpp the planner is a stub, so the rest of the
// backend builds and tests without a C++ toolchain.
func TestWithoutCppThePlannerIsUnavailable(t *testing.T) {
	if planner.Available() || planner.Version() != "" {
		t.Errorf("Available() = %v, Version() = %q", planner.Available(), planner.Version())
	}
	p := planner.New()
	if _, err := p.Route(context.Background(), planner.Area{}, planner.Settings{}, geo.Point{}); !errors.Is(err, planner.ErrUnavailable) {
		t.Errorf("Route: %v", err)
	}
	if _, err := p.Way(context.Background(), planner.Area{}, geo.Point{}, geo.Point{}); !errors.Is(err, planner.ErrUnavailable) {
		t.Errorf("Way: %v", err)
	}
}
