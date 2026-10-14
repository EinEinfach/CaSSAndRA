package server_test

import (
	"bufio"
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/server"
)

// stream connects to the hub and returns a function that reads the next
// SSE block ("event: x\ndata: y" or ": keep-alive").
func stream(t *testing.T, url string) (next func() string, closeFn func()) {
	t.Helper()
	ctx, cancel := context.WithCancel(context.Background())
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		t.Fatal(err)
	}
	res, err := http.DefaultClient.Do(req) //nolint:bodyclose // closed by the returned closeFn
	if err != nil {
		t.Fatal(err)
	}
	if ct := res.Header.Get("Content-Type"); ct != "text/event-stream" {
		t.Fatalf("Content-Type = %q", ct)
	}
	lines := make(chan string)
	go func() {
		defer close(lines)
		sc := bufio.NewScanner(res.Body)
		var block []string
		for sc.Scan() {
			if sc.Text() == "" {
				lines <- strings.Join(block, "\n")
				block = nil
				continue
			}
			block = append(block, sc.Text())
		}
	}()
	next = func() string {
		t.Helper()
		select {
		case b := <-lines:
			return b
		case <-time.After(2 * time.Second):
			t.Fatal("no event within 2 s")
			return ""
		}
	}
	return next, func() { cancel(); _ = res.Body.Close() }
}

func waitClients(t *testing.T, h *server.Hub, n int) {
	t.Helper()
	deadline := time.Now().Add(2 * time.Second)
	for h.Clients() != n {
		if time.Now().After(deadline) {
			t.Fatalf("clients = %d, want %d", h.Clients(), n)
		}
		time.Sleep(time.Millisecond)
	}
}

func TestHubReplaysLatestEventsThenStreams(t *testing.T) {
	hub := server.NewHub(time.Hour)
	hub.Publish("robot", []byte(`{"v":1}`))
	hub.Publish("map", []byte(`{"m":1}`))
	hub.Publish("robot", []byte(`{"v":2}`))
	srv := httptest.NewServer(hub)
	defer srv.Close()

	next, closeFn := stream(t, srv.URL)
	defer closeFn()
	if got := next(); got != "event: robot\ndata: {\"v\":2}" {
		t.Errorf("first replay = %q, want latest robot event", got)
	}
	if got := next(); got != "event: map\ndata: {\"m\":1}" {
		t.Errorf("second replay = %q, want map event", got)
	}

	hub.Publish("robot", []byte(`{"v":3}`))
	if got := next(); got != "event: robot\ndata: {\"v\":3}" {
		t.Errorf("live event = %q", got)
	}
}

func TestHubBroadcastsToAllClients(t *testing.T) {
	hub := server.NewHub(time.Hour)
	srv := httptest.NewServer(hub)
	defer srv.Close()
	a, closeA := stream(t, srv.URL)
	defer closeA()
	b, closeB := stream(t, srv.URL)
	defer closeB()
	waitClients(t, hub, 2)

	hub.Publish("robot", []byte("1"))
	for name, next := range map[string]func() string{"a": a, "b": b} {
		if got := next(); got != "event: robot\ndata: 1" {
			t.Errorf("client %s got %q", name, got)
		}
	}
}

func TestHubSendsHeartbeat(t *testing.T) {
	hub := server.NewHub(20 * time.Millisecond)
	srv := httptest.NewServer(hub)
	defer srv.Close()
	next, closeFn := stream(t, srv.URL)
	defer closeFn()
	if got := next(); got != ": keep-alive" {
		t.Errorf("got %q, want keep-alive comment", got)
	}
}

func TestHubForgetsDisconnectedClients(t *testing.T) {
	hub := server.NewHub(time.Hour)
	srv := httptest.NewServer(hub)
	defer srv.Close()
	_, closeFn := stream(t, srv.URL)
	waitClients(t, hub, 1)
	closeFn()
	waitClients(t, hub, 0)
}

// blockedWriter never accepts data, like a client that stopped reading.
type blockedWriter struct {
	header http.Header
	block  chan struct{}
}

func (w *blockedWriter) Header() http.Header         { return w.header }
func (w *blockedWriter) WriteHeader(int)             {}
func (w *blockedWriter) Write(p []byte) (int, error) { <-w.block; return len(p), nil }
func (w *blockedWriter) Flush()                      {}

func TestHubPublishNeverBlocksOnSlowClients(t *testing.T) {
	hub := server.NewHub(time.Hour)
	hub.Publish("robot", []byte("0")) // the replay blocks the handler
	w := &blockedWriter{header: http.Header{}, block: make(chan struct{})}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() {
		hub.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/", nil).WithContext(ctx))
		close(done)
	}()
	waitClients(t, hub, 1)

	published := make(chan struct{})
	go func() {
		for i := range 1000 {
			hub.Publish("robot", []byte{byte('0' + i%10)})
		}
		close(published)
	}()
	select {
	case <-published:
	case <-time.After(2 * time.Second):
		t.Fatal("Publish blocked on a slow client")
	}
	cancel()
	close(w.block)
	<-done
}

// plainWriter cannot flush, so streaming is impossible. It forwards only the
// http.ResponseWriter methods (embedding the recorder would inherit Flush).
type plainWriter struct{ rec *httptest.ResponseRecorder }

func (w plainWriter) Header() http.Header         { return w.rec.Header() }
func (w plainWriter) Write(p []byte) (int, error) { return w.rec.Write(p) }
func (w plainWriter) WriteHeader(code int)        { w.rec.WriteHeader(code) }

func TestHubNeedsFlusher(t *testing.T) {
	hub := server.NewHub(time.Hour)
	rec := httptest.NewRecorder()
	hub.ServeHTTP(plainWriter{rec}, httptest.NewRequest(http.MethodGet, "/", nil))
	if rec.Code != http.StatusInternalServerError {
		t.Errorf("status = %d, want 500", rec.Code)
	}
}

func TestServerMountsEventsAndRoutes(t *testing.T) {
	hub := server.NewHub(time.Hour)
	feature := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) { _, _ = w.Write([]byte("feature")) })
	h := server.New(server.Options{UI: builtUI, Events: hub, Routes: map[string]http.Handler{"/api/robot/": feature}})

	srv := httptest.NewServer(h)
	defer srv.Close()
	_, closeFn := stream(t, srv.URL+"/api/events")
	closeFn()

	rec := get(t, h, "/api/robot/state")
	if rec.Body.String() != "feature" {
		t.Errorf("/api/robot/state = %q, want feature handler", rec.Body.String())
	}
	if rec := get(t, h, "/api/other"); rec.Code != http.StatusNotFound {
		t.Errorf("/api/other = %d, want 404", rec.Code)
	}
}
