package app_test

import (
	"context"
	"errors"
	"regexp"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/app"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
)

func TestCheckPlanner(t *testing.T) {
	var out strings.Builder
	err := app.CheckPlanner(context.Background(), &out)
	if !planner.Available() {
		if !errors.Is(err, planner.ErrUnavailable) || out.Len() != 0 {
			t.Errorf("without the planner: err = %v, output %q", err, out.String())
		}
		return
	}
	if err != nil {
		t.Fatal(err)
	}
	want := regexp.MustCompile(`^planner 1\.4: route through the demo garden with \d{3,} points in \d+`)
	if !want.MatchString(out.String()) {
		t.Errorf("output %q", out.String())
	}
}
