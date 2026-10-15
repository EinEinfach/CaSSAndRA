package settings_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

func newStoreWithSecrets(t *testing.T) *settings.Store {
	t.Helper()
	s, err := settings.Open(filepath.Join(t.TempDir(), "settings.json"))
	if err != nil {
		t.Fatal(err)
	}
	cur := settings.Default()
	cur.Connection.HTTPPassword = 1234
	cur.Connection.MQTTPassword = "mqttpw"
	cur.API.Password = "apipw"
	if err := s.Set(cur); err != nil {
		t.Fatal(err)
	}
	return s
}

func call(t *testing.T, h http.Handler, method, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, "/api/settings", strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestAPIGetHidesPasswords(t *testing.T) {
	s := newStoreWithSecrets(t)
	rec := call(t, s.Handler(), http.MethodGet, "")
	if rec.Code != http.StatusOK || rec.Header().Get("Content-Type") != "application/json" {
		t.Fatalf("status %d, content type %q", rec.Code, rec.Header().Get("Content-Type"))
	}
	body := rec.Body.String()
	for _, secret := range []string{"1234", "mqttpw", "apipw"} {
		if strings.Contains(body, secret) {
			t.Errorf("response contains password %q: %s", secret, body)
		}
	}
	var v settings.View
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatal(err)
	}
	if v.Secrets != (settings.Secrets{HTTPPassword: true, MQTTPassword: true, APIPassword: true}) {
		t.Errorf("secrets = %+v, want all set", v.Secrets)
	}
}

func TestAPIPutChangesOnlyGivenFields(t *testing.T) {
	s := newStoreWithSecrets(t)
	rec := call(t, s.Handler(), http.MethodPut, `{"settings": {"rover": {"mowSpeedMps": 0.5}}}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status %d: %s", rec.Code, rec.Body)
	}
	got := s.Get()
	if got.Rover.MowSpeedMps != 0.5 || got.Rover.GotoSpeedMps != settings.Default().Rover.GotoSpeedMps {
		t.Errorf("rover = %+v", got.Rover)
	}
	if got.Connection.HTTPPassword != 1234 || got.Connection.MQTTPassword != "mqttpw" || got.API.Password != "apipw" {
		t.Error("passwords changed although the body did not set them")
	}
	if strings.Contains(rec.Body.String(), "mqttpw") {
		t.Error("PUT response contains a password")
	}
}

func TestAPIPutViewBackKeepsPasswords(t *testing.T) {
	s := newStoreWithSecrets(t)
	view := call(t, s.Handler(), http.MethodGet, "").Body.String()
	// The browser sends the settings it got back; their passwords are empty.
	var v settings.View
	_ = json.Unmarshal([]byte(view), &v)
	body, _ := json.Marshal(map[string]any{"settings": v.Settings})
	if rec := call(t, s.Handler(), http.MethodPut, string(body)); rec.Code != http.StatusOK {
		t.Fatalf("status %d: %s", rec.Code, rec.Body)
	}
	if got := s.Get(); got.Connection.HTTPPassword != 1234 || got.Connection.MQTTPassword != "mqttpw" || got.API.Password != "apipw" {
		t.Errorf("passwords were cleared: %+v %+v", got.Connection, got.API)
	}
}

func TestAPIPutPasswords(t *testing.T) {
	s := newStoreWithSecrets(t)
	rec := call(t, s.Handler(), http.MethodPut, `{"passwords": {"httpPassword": 0, "mqttPassword": "new", "apiPassword": null}}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status %d: %s", rec.Code, rec.Body)
	}
	got := s.Get()
	if got.Connection.HTTPPassword != 0 || got.Connection.MQTTPassword != "new" || got.API.Password != "apipw" {
		t.Errorf("got http %d, mqtt %q, api %q; want removed, new, kept",
			got.Connection.HTTPPassword, got.Connection.MQTTPassword, got.API.Password)
	}
	var v settings.View
	_ = json.Unmarshal(rec.Body.Bytes(), &v)
	if v.Secrets != (settings.Secrets{MQTTPassword: true, APIPassword: true}) {
		t.Errorf("secrets = %+v", v.Secrets)
	}
}

func TestAPIPutErrors(t *testing.T) {
	tests := []struct {
		name, body string
		want       int
	}{
		{"invalid value", `{"settings": {"planner": {"pattern": "spiral"}}}`, http.StatusBadRequest},
		{"unknown field", `{"settings": {"rover": {"speed": 1}}}`, http.StatusBadRequest},
		{"unknown top level field", `{"rover": {}}`, http.StatusBadRequest},
		{"not json", `{`, http.StatusBadRequest},
		{"wrong type", `{"settings": {"rover": {"mowSpeedMps": "fast"}}}`, http.StatusBadRequest},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := newStoreWithSecrets(t)
			before := s.Get()
			rec := call(t, s.Handler(), http.MethodPut, tt.body)
			if rec.Code != tt.want || !strings.Contains(rec.Body.String(), `"error"`) {
				t.Errorf("status %d body %s, want %d with error", rec.Code, rec.Body, tt.want)
			}
			if s.Get() != before {
				t.Error("settings changed")
			}
		})
	}
}
