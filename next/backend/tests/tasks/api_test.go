package tasks_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

func httptestRequest(method, path string) *http.Request {
	return httptest.NewRequest(method, path, http.NoBody)
}

func serve(h http.Handler, req *http.Request) *httptest.ResponseRecorder {
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

// do sends a request to the preview endpoint.
func do(t *testing.T, h http.Handler, method, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, "/api/tasks/preview", strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

const previewBody = `{"selection":[{"x":1,"y":1},{"x":3,"y":1},{"x":3,"y":3}],
	"parameters":{"pattern":"lines","widthM":0.2,"angleDeg":0,"distanceToBorder":1,
	"mowArea":true,"borderLaps":1,"mowExclusions":true,"borderCcw":false}}`

func TestAPIPreviewRoundTrip(t *testing.T) {
	f := newFixture(t)
	h := f.svc.Handler()

	rec := do(t, h, "GET", "")
	if rec.Code != http.StatusOK || strings.TrimSpace(rec.Body.String()) != `{"plan":null}` {
		t.Fatalf("GET without plan = %d %s", rec.Code, rec.Body)
	}

	rec = do(t, h, "POST", previewBody)
	if rec.Code != http.StatusOK {
		t.Fatalf("POST = %d %s", rec.Code, rec.Body)
	}
	var plan struct {
		MapID     string      `json:"mapId"`
		Route     []geo.Point `json:"route"`
		Selection []geo.Point `json:"selection"`
		Start     geo.Point   `json:"start"`
		DistanceM float64     `json:"distanceM"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &plan); err != nil {
		t.Fatal(err)
	}
	if plan.MapID != f.mapID || len(plan.Route) != 5 || len(plan.Selection) != 3 || plan.DistanceM <= 0 {
		t.Errorf("plan = %+v", plan)
	}

	rec = do(t, h, "GET", "")
	var got tasks.PlanJSON
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil || got.Plan == nil || len(got.Plan.Route) != 5 {
		t.Errorf("GET after POST = %s (%v)", rec.Body, err)
	}

	if rec := do(t, h, "DELETE", ""); rec.Code != http.StatusNoContent {
		t.Errorf("DELETE = %d", rec.Code)
	}
	if f.svc.Current() != nil {
		t.Error("plan still there after DELETE")
	}
}

func TestAPIErrors(t *testing.T) {
	tests := []struct {
		name  string
		setup func(f *fixture)
		body  string
		want  int
	}{
		{"broken JSON", nil, `{`, http.StatusBadRequest},
		{"unknown field", nil, `{"parameters":{},"color":"red"}`, http.StatusBadRequest},
		{"invalid parameters", nil, `{"parameters":{"pattern":"spiral"}}`, http.StatusBadRequest},
		{"no active map", func(f *fixture) { _ = f.maps.SetActive("") }, previewBody, http.StatusConflict},
		{"planner not built in", func(f *fixture) {
			f.planner.RouteFunc = func(planner.Area, planner.Settings, geo.Point) ([]geo.Point, error) {
				return nil, planner.ErrUnavailable
			}
		}, previewBody, http.StatusNotImplemented},
		{"planner too slow", func(f *fixture) {
			f.planner.RouteFunc = func(planner.Area, planner.Settings, geo.Point) ([]geo.Point, error) {
				return nil, context.DeadlineExceeded
			}
		}, previewBody, http.StatusGatewayTimeout},
		{"planner failed", func(f *fixture) {
			f.planner.RouteFunc = func(planner.Area, planner.Settings, geo.Point) ([]geo.Point, error) {
				return nil, planner.ErrFailed
			}
		}, previewBody, http.StatusInternalServerError},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			if tt.setup != nil {
				tt.setup(f)
			}
			rec := do(t, f.svc.Handler(), "POST", tt.body)
			if rec.Code != tt.want {
				t.Errorf("status = %d, want %d (%s)", rec.Code, tt.want, rec.Body)
			}
			var body struct {
				Error string `json:"error"`
			}
			if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil || body.Error == "" {
				t.Errorf("body = %s, want {\"error\": ...}", rec.Body)
			}
		})
	}
}
