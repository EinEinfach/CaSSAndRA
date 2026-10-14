package app_test

import (
	"context"
	"encoding/json"
	"net"
	"net/http"
	"testing"
	"testing/fstest"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/app"
	"github.com/EinEinfach/CaSSAndRA/next/backend/server"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func start(t *testing.T) (baseURL string, cancel context.CancelFunc, done <-chan error) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	ctx, cancel := context.WithCancel(t.Context())
	errc := make(chan error, 1)
	go func() {
		errc <- app.Run(ctx, app.Config{
			Version: "test",
			UI:      fstest.MapFS{"index.html": {Data: []byte("ui")}},
			Logger:  testkit.Logger(t),
		}, ln)
	}()
	return "http://" + ln.Addr().String(), cancel, errc
}

func getHealth(baseURL string) (server.Health, error) {
	var h server.Health
	res, err := http.Get(baseURL + "/api/health")
	if err != nil {
		return h, err
	}
	defer func() { _ = res.Body.Close() }()
	err = json.NewDecoder(res.Body).Decode(&h)
	return h, err
}

func TestRunServesHealth(t *testing.T) {
	baseURL, cancel, done := start(t)
	defer func() {
		cancel()
		<-done
	}()

	got, err := getHealth(baseURL)
	if err != nil {
		t.Fatalf("GET health: %v", err)
	}
	if got.Version != "test" {
		t.Errorf("version = %q, want test", got.Version)
	}
}

func TestRunShutsDownOnCancel(t *testing.T) {
	baseURL, cancel, done := start(t)
	if _, err := getHealth(baseURL); err != nil {
		t.Fatalf("server not up: %v", err)
	}

	cancel()

	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("Run returned %v, want nil", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Run did not return after cancel")
	}
	if _, err := getHealth(baseURL); err == nil {
		t.Error("server still accepts requests after shutdown")
	}
}

func TestRunFailsOnClosedListener(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	_ = ln.Close()

	if err := app.Run(t.Context(), app.Config{UI: fstest.MapFS{}}, ln); err == nil {
		t.Fatal("Run on a closed listener returned nil, want error")
	}
}
