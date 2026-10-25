package schedule_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/schedule"
)

func call(h http.Handler, method, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, "/api/schedule", strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestAPIGet(t *testing.T) {
	f := newFixture(t)
	f.plan(t, 0, "09:00", "12:00", "front")
	rec := call(f.runner.Handler(), http.MethodGet, "")
	var got schedule.JSON
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil || rec.Code != http.StatusOK {
		t.Fatalf("GET = %d %s", rec.Code, rec.Body)
	}
	if got.Status.State != schedule.StateWaiting || got.Status.Next != monday.Add(9*time.Hour).Format(time.RFC3339) {
		t.Errorf("status = %+v", got.Status)
	}
	if !strings.Contains(rec.Body.String(), `"taskIds":[]`) {
		t.Errorf("empty task lists must be [], not null: %s", rec.Body)
	}
}

func TestAPIPut(t *testing.T) {
	day := func(tasks string) string {
		return `{"schedule":{"active":true,"days":[{"start":"09:00","end":"12:00","taskIds":[` + tasks + `]}` +
			strings.Repeat(`,{"start":"12:00","end":"12:00","taskIds":[]}`, 6) + `]}}`
	}
	tests := []struct {
		name, body string
		want       int
	}{
		{"valid", day(`"front","back"`), http.StatusOK},
		{"unknown task", day(`"nope"`), http.StatusBadRequest},
		{"tasks of two maps", day(`"front","other"`), http.StatusBadRequest},
		{"invalid time", strings.Replace(day(""), "09:00", "9", 1), http.StatusBadRequest},
		{"missing days", `{"schedule":{"active":true,"days":[]}}`, http.StatusBadRequest},
		{"not wrapped", `{"active":true}`, http.StatusBadRequest},
		{"unknown field", `{"schedule":{"active":true,"weeks":1}}`, http.StatusBadRequest},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			rec := call(f.runner.Handler(), http.MethodPut, tt.body)
			if rec.Code != tt.want {
				t.Fatalf("PUT = %d %s, want %d", rec.Code, rec.Body, tt.want)
			}
			if tt.want == http.StatusOK && !f.store.Get().Active {
				t.Error("schedule not stored")
			}
			if tt.want != http.StatusOK && f.store.Get().Active {
				t.Error("rejected schedule was stored")
			}
		})
	}
}
