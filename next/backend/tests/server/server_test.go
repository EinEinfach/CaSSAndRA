package server_test

import (
	"encoding/json"
	"io/fs"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/EinEinfach/CaSSAndRA/next/backend/server"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

var builtUI = fstest.MapFS{
	"index.html":          {Data: []byte("<html>index</html>")},
	"_app/immutable/a.js": {Data: []byte("console.log(1)")},
}

func newHandler(t *testing.T, ui fs.FS) http.Handler {
	t.Helper()
	return server.New(server.Options{Version: "1.2.3", UI: ui, Logger: testkit.Logger(t)})
}

func get(t *testing.T, h http.Handler, target string) *httptest.ResponseRecorder {
	t.Helper()
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, target, nil))
	return rec
}

func TestHealth(t *testing.T) {
	rec := get(t, newHandler(t, builtUI), "/api/health")

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	var got server.Health
	if err := json.NewDecoder(rec.Body).Decode(&got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if want := (server.Health{Status: "ok", Version: "1.2.3"}); got != want {
		t.Errorf("health = %+v, want %+v", got, want)
	}
}

func TestHealthRejectsOtherMethods(t *testing.T) {
	rec := httptest.NewRecorder()
	newHandler(t, builtUI).ServeHTTP(rec, httptest.NewRequest(http.MethodPost, "/api/health", nil))

	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want 405", rec.Code)
	}
}

func TestStaticAndSPARouting(t *testing.T) {
	tests := []struct {
		name       string
		ui         fs.FS
		path       string
		wantStatus int
		wantBody   string
	}{
		{"root serves index", builtUI, "/", 200, "<html>index</html>"},
		{"asset is served as file", builtUI, "/_app/immutable/a.js", 200, "console.log(1)"},
		{"client route falls back to index", builtUI, "/maps/edit", 200, "<html>index</html>"},
		{"directory falls back to index", builtUI, "/_app", 200, "<html>index</html>"},
		{"unknown api route is 404, not index", builtUI, "/api/nope", 404, `{"error":"not found"}`},
		{"missing build gives a hint", fstest.MapFS{}, "/", 404, "UI not built"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := get(t, newHandler(t, tt.ui), tt.path)

			if rec.Code != tt.wantStatus {
				t.Errorf("status = %d, want %d", rec.Code, tt.wantStatus)
			}
			if b := rec.Body.String(); !strings.Contains(b, tt.wantBody) {
				t.Errorf("body = %q, want it to contain %q", b, tt.wantBody)
			}
		})
	}
}

func TestEmbeddedUIIsReadable(t *testing.T) {
	if _, err := fs.ReadDir(server.EmbeddedUI(), "."); err != nil {
		t.Fatalf("read embedded UI: %v", err)
	}
}
