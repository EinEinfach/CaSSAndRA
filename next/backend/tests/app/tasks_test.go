package app_test

import (
	"encoding/json"
	"net/http"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func TestPreviewIsSharedAndDroppedWhenTheMapChanges(t *testing.T) {
	cfg := testConfig(t)
	fake := &testkit.FakePlanner{}
	cfg.Planner = fake
	r := startWith(t, cfg)
	events := streamEvents(t, r.baseURL, "plan")
	next := func() *tasks.Plan {
		t.Helper()
		select {
		case data := <-events:
			var p tasks.PlanJSON
			if err := json.Unmarshal([]byte(data), &p); err != nil {
				t.Fatal(err)
			}
			return p.Plan
		case <-time.After(3 * time.Second):
			t.Fatal("no plan event")
			return nil
		}
	}
	if p := next(); p != nil {
		t.Fatalf("first event = %+v, want no plan", p)
	}

	code, body := send(t, http.MethodPost, r.baseURL+"/api/maps",
		`{"name": "Back", "perimeter": [{"x":0,"y":0},{"x":8,"y":0},{"x":8,"y":8},{"x":0,"y":8}]}`)
	if code != http.StatusCreated {
		t.Fatalf("POST map = %d %s", code, body)
	}
	var m maps.Map
	_ = json.Unmarshal([]byte(body), &m)
	if code, body := send(t, http.MethodPut, r.baseURL+"/api/maps/active", `{"id":"`+m.ID+`"}`); code != http.StatusNoContent {
		t.Fatalf("activate = %d %s", code, body)
	}

	code, body = send(t, http.MethodPost, r.baseURL+"/api/tasks/preview",
		`{"parameters":{"pattern":"rings","widthM":0.18,"angleDeg":0,"distanceToBorder":1,"mowArea":true,"borderLaps":1,"mowExclusions":false,"borderCcw":false}}`)
	if code != http.StatusOK {
		t.Fatalf("preview = %d %s", code, body)
	}
	if p := next(); p == nil || p.MapID != m.ID || len(p.Route) != 5 {
		t.Fatalf("plan event = %+v", p)
	}
	if calls := fake.Routes(); len(calls) != 1 || len(calls[0].Area.Perimeter) != 4 {
		t.Errorf("planner calls = %+v", calls)
	}

	if code, body := send(t, http.MethodPut, r.baseURL+"/api/maps/"+m.ID,
		`{"name": "Back", "perimeter": [{"x":0,"y":0},{"x":9,"y":0},{"x":9,"y":9},{"x":0,"y":9}]}`); code != http.StatusOK {
		t.Fatalf("PUT map = %d %s", code, body)
	}
	if p := next(); p != nil {
		t.Errorf("plan after editing the map = %+v, want none", p)
	}
}

func TestPreviewWithTheBuiltInPlanner(t *testing.T) {
	r := start(t)
	code, body := send(t, http.MethodPost, r.baseURL+"/api/maps",
		`{"name": "Back", "perimeter": [{"x":0,"y":0},{"x":8,"y":0},{"x":8,"y":8},{"x":0,"y":8}]}`)
	if code != http.StatusCreated {
		t.Fatalf("POST map = %d %s", code, body)
	}
	var m maps.Map
	_ = json.Unmarshal([]byte(body), &m)
	if code, body := send(t, http.MethodPut, r.baseURL+"/api/maps/active", `{"id":"`+m.ID+`"}`); code != http.StatusNoContent {
		t.Fatalf("activate = %d %s", code, body)
	}
	// A selection over the corner of the garden: lanes only in 0..4 x 0..4.
	code, body = send(t, http.MethodPost, r.baseURL+"/api/tasks/preview",
		`{"selection":[{"x":-4,"y":-4},{"x":4,"y":-4},{"x":4,"y":4},{"x":-4,"y":4}],
		"parameters":{"pattern":"lines","widthM":0.25,"angleDeg":30,"distanceToBorder":1,"mowArea":true,"borderLaps":1,"mowExclusions":false,"borderCcw":false}}`)
	if !planner.Available() {
		if code != http.StatusNotImplemented {
			t.Errorf("preview without planner = %d %s, want 501", code, body)
		}
		return
	}
	if code != http.StatusOK {
		t.Fatalf("preview = %d %s", code, body)
	}
	var p tasks.Plan
	if err := json.Unmarshal([]byte(body), &p); err != nil {
		t.Fatal(err)
	}
	if len(p.Route) < 20 {
		t.Fatalf("route of %d points", len(p.Route))
	}
	// The robot of the simulator starts outside the new map: nearest corner.
	for i, pt := range p.Route[1:] {
		if pt.X < -1e-6 || pt.X > 4+1e-6 || pt.Y < -1e-6 || pt.Y > 4+1e-6 {
			t.Fatalf("point %d %v outside the selected part", i+1, pt)
		}
	}
}
