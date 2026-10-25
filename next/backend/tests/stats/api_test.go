package stats_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/stats"
)

func get(h http.Handler, url string) *httptest.ResponseRecorder {
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, url, nil))
	return rec
}

func TestAPIDefaultsToTheLastDay(t *testing.T) {
	s, _ := open(t)
	now := t0.Add(12 * time.Hour)
	for _, at := range []time.Time{now.Add(-25 * time.Hour), now.Add(-time.Hour)} {
		if err := s.AddSample(ctx, stats.Sample{T: at, BatteryV: 26}); err != nil {
			t.Fatal(err)
		}
	}
	rec := get(s.Handler(func() time.Time { return now }), "/api/stats")
	var got stats.JSON
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil || rec.Code != http.StatusOK {
		t.Fatalf("GET = %d %s", rec.Code, rec.Body)
	}
	if !got.To.Equal(now) || !got.From.Equal(now.Add(-24*time.Hour)) || len(got.Samples) != 1 {
		t.Errorf("got %v to %v with %d samples, want the last 24 h with 1", got.From, got.To, len(got.Samples))
	}
	if _, ok := got.Totals["mowSec"]; !ok {
		t.Errorf("totals = %v", got.Totals)
	}
}

func TestAPIRange(t *testing.T) {
	s, _ := open(t)
	h := s.Handler(func() time.Time { return t0 })
	tests := []struct {
		query string
		want  int
	}{
		{"?from=2026-10-20T00:00:00Z&to=2026-10-27T00:00:00Z&points=50", http.StatusOK},
		{"?from=2026-10-20T00:00:00%2B01:00&to=2026-10-21T00:00:00%2B01:00", http.StatusOK},
		{"?from=yesterday", http.StatusBadRequest},
		{"?from=2026-10-27T00:00:00Z&to=2026-10-20T00:00:00Z", http.StatusBadRequest},
		{"?from=2020-01-01T00:00:00Z&to=2026-01-01T00:00:00Z", http.StatusBadRequest},
		{"?points=0", http.StatusBadRequest},
		{"?points=100000", http.StatusBadRequest},
	}
	for _, tt := range tests {
		rec := get(h, "/api/stats"+tt.query)
		if rec.Code != tt.want {
			t.Errorf("%s = %d %s, want %d", tt.query, rec.Code, rec.Body, tt.want)
		}
		if tt.want == http.StatusOK && !strings.Contains(rec.Body.String(), `"samples":[]`) {
			t.Errorf("%s: empty samples must be [], got %s", tt.query, rec.Body)
		}
	}
}
