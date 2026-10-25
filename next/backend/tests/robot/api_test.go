package robot_test

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"net/http/httptest"
	"reflect"
	"slices"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
)

func call(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(method, path, strings.NewReader(body)))
	return rec
}

func TestAPIState(t *testing.T) {
	f := newFixture(t)
	h := f.robot.Handler()

	rec := call(t, h, http.MethodGet, "/api/robot/state", "")
	if rec.Code != http.StatusOK || rec.Header().Get("Content-Type") != "application/json" {
		t.Fatalf("status %d, content type %q", rec.Code, rec.Header().Get("Content-Type"))
	}
	if !strings.Contains(rec.Body.String(), `"status":"offline"`) || !strings.Contains(rec.Body.String(), `"updatedAt":null`) {
		t.Errorf("state before connecting = %s", rec.Body.String())
	}

	s := state(protocol.OpMow)
	s.X, s.Y, s.AccuracyM, s.HeadingRad = 1.5, 2.5, math.NaN(), 1.2
	f.online(s)
	rec = call(t, h, http.MethodGet, "/api/robot/state", "")
	var got map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode %s: %v", rec.Body.String(), err)
	}
	want := map[string]any{
		"status": "transit", "online": true, "position": map[string]any{"x": 1.5, "y": 2.5},
		"accuracyM": 0.0, "headingRad": 1.2, "op": "mow", "solution": "fix", "sensor": "none",
		"socPercent": 67.0, "mowMotorOn": false, "updatedAt": t0.Format(time.RFC3339),
	}
	for k, v := range want {
		if !reflect.DeepEqual(got[k], v) {
			t.Errorf("%s = %#v, want %#v", k, got[k], v)
		}
	}
}

func TestAPIMap(t *testing.T) {
	f := newFixture(t)
	h := f.robot.Handler()

	rec := call(t, h, http.MethodGet, "/api/robot/map", "")
	if rec.Body.String() != `{"perimeter":[],"exclusions":[],"dock":[],"way":[]}`+"\n" {
		t.Errorf("empty map = %s, want empty lists, not null", rec.Body.String())
	}

	m := protocol.Map{Perimeter: pts(0, 0, 1, 0, 1, 1), Exclusions: [][]geo.Point{nil}, Way: pts(0.5, 0.5)}
	if err := f.robot.UploadMap(context.Background(), m); err != nil {
		t.Fatal(err)
	}
	var got robot.MapJSON
	if err := json.Unmarshal(call(t, h, http.MethodGet, "/api/robot/map", "").Body.Bytes(), &got); err != nil {
		t.Fatal(err)
	}
	if len(got.Perimeter) != 3 || len(got.Way) != 1 || got.Exclusions[0] == nil || got.Dock == nil {
		t.Errorf("map = %+v", got)
	}
}

func TestAdoptMapSendsNothing(t *testing.T) {
	f := newFixture(t)
	m := protocol.Map{Perimeter: pts(0, 0, 1, 0, 1, 1), Way: pts(0.5, 0.5)}
	f.robot.AdoptMap(m)
	if got := f.robot.Map(); len(got.Perimeter) != 3 || len(got.Way) != 1 {
		t.Errorf("Map() = %+v, want the adopted map", got)
	}
	if sent := f.sender.payloads(); len(sent) != 0 {
		t.Errorf("sent %q, want nothing", sent)
	}
}

func TestAPICommands(t *testing.T) {
	tests := []struct {
		path, body, want string
	}{
		{"/api/robot/stop", "", "AT+C,0,0,-1,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"/api/robot/dock", "", "AT+C,0,4,-1,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"/api/robot/mow", "", "AT+C,1,1,0.25,60,0,-1,-1,-1,-1,-1,1"},
		{"/api/robot/goto", "", "AT+C,0,1,0.3,60,0,-1,-1,-1,-1,-1,0"},
		{"/api/robot/skip-next-point", "", "AT+C,-1,-1,-1,-1,-1,-1,1,-1,-1,-1,-1"},
		{"/api/robot/reboot", "", "AT+Y"},
		{"/api/robot/reboot-gps", "", "AT+Y2"},
		{"/api/robot/shutdown", "", "AT+Y3"},
		{"/api/robot/move", `{"linear":0.3,"angular":-0.5}`, "AT+M,0.3,-0.5"},
		{"/api/robot/move", `{"linear":0,"angular":0}`, "AT+M,0,0"},
		{"/api/robot/mow-motor", `{"on":true}`, "AT+C,1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"/api/robot/speed", `{"mps":0.4}`, "AT+C,-1,-1,0.4,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"/api/robot/skip-to-progress", `{"fraction":0.5}`, "AT+C,-1,-1,-1,-1,-1,0.5,-1,-1,-1,-1,-1"},
	}
	for _, tt := range tests {
		t.Run(tt.path+" "+tt.body, func(t *testing.T) {
			f := newFixture(t)
			rec := call(t, f.robot.Handler(), http.MethodPost, tt.path, tt.body)
			if rec.Code != http.StatusNoContent {
				t.Fatalf("status = %d, body %s", rec.Code, rec.Body.String())
			}
			if got := f.sender.payloads(); !reflect.DeepEqual(got, []string{tt.want}) {
				t.Errorf("sent %q, want %q", got, tt.want)
			}
		})
	}
}

func TestAPIRejectsBadInput(t *testing.T) {
	tests := []struct{ path, body string }{
		{"/api/robot/move", ``},
		{"/api/robot/move", `{"linear":0.3}`},
		{"/api/robot/move", `{"linear":1.5,"angular":0}`},
		{"/api/robot/move", `{"linear":0,"angular":-2.5}`},
		{"/api/robot/move", `{"linear":0,"angular":0,"turbo":true}`},
		{"/api/robot/move", `{"linear":"fast","angular":0}`},
		{"/api/robot/mow-motor", `{}`},
		{"/api/robot/speed", `{"mps":-0.1}`},
		{"/api/robot/speed", `{"mps":1.1}`},
		{"/api/robot/skip-to-progress", `{"fraction":1.5}`},
		{"/api/robot/skip-to-progress", `{"fraction":-0.5}`},
		{"/api/robot/move", `{"linear":0,"angular":0,"pad":"` + strings.Repeat("x", 70000) + `"}`},
	}
	for _, tt := range tests {
		f := newFixture(t)
		rec := call(t, f.robot.Handler(), http.MethodPost, tt.path, tt.body)
		if rec.Code != http.StatusBadRequest || !strings.Contains(rec.Body.String(), `"error"`) {
			name := tt.body
			if len(name) > 60 {
				name = name[:60] + "..."
			}
			t.Errorf("POST %s %s = %d %s, want 400 with error", tt.path, name, rec.Code, rec.Body.String())
		}
		if sent := f.sender.payloads(); len(sent) != 0 {
			t.Errorf("POST %s sent %q despite bad input", tt.path, sent)
		}
	}
}

func TestAPIMapsErrorsToStatus(t *testing.T) {
	f := newFixture(t)
	h := f.robot.Handler()

	f.sender.replies["AT+C"] = ""
	f.sender.fail["AT+C"] = 1
	if rec := call(t, h, http.MethodPost, "/api/robot/dock", ""); rec.Code != http.StatusBadGateway {
		t.Errorf("link error -> %d, want 502", rec.Code)
	}

	offline := robot.New(offlineSender{}, robot.DefaultConfig())
	if rec := call(t, offline.Handler(), http.MethodPost, "/api/robot/dock", ""); rec.Code != http.StatusServiceUnavailable {
		t.Errorf("offline -> %d, want 503", rec.Code)
	}

	f.sender.block["AT+C"] = true
	go func() { <-f.sender.blocked }()
	ctx, cancel := context.WithTimeout(context.Background(), time.Millisecond)
	defer cancel()
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodPost, "/api/robot/mow", nil).WithContext(ctx))
	if rec.Code != http.StatusGatewayTimeout {
		t.Errorf("timeout -> %d, want 504", rec.Code)
	}

	if rec := call(t, h, http.MethodGet, "/api/robot/stop", ""); rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("GET stop -> %d, want 405", rec.Code)
	}
}

type offlineSender struct{}

func (offlineSender) Send(context.Context, string) (string, error) {
	return "", fmt.Errorf("send: %w", link.ErrOffline)
}

func TestPublishStateOnlyOnChange(t *testing.T) {
	f := newFixture(t)
	var mu sync.Mutex
	var published []string
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() {
		f.robot.PublishState(ctx, time.Millisecond, func(b []byte) {
			mu.Lock()
			published = append(published, string(b))
			mu.Unlock()
		})
		close(done)
	}()
	snapshot := func() []string { mu.Lock(); defer mu.Unlock(); return slices.Clone(published) }
	waitUntil := func(ok func([]string) bool) {
		t.Helper()
		deadline := time.Now().Add(2 * time.Second)
		for !ok(snapshot()) && time.Now().Before(deadline) {
			time.Sleep(time.Millisecond)
		}
	}

	waitUntil(func(p []string) bool { return len(p) >= 1 })
	time.Sleep(20 * time.Millisecond) // many ticks without changes
	if n := len(snapshot()); n != 1 {
		t.Errorf("published %d times without changes, want 1", n)
	}

	// Going online and the first state are two changes; a tick may fall in
	// between, so the intermediate state may be published too.
	f.online(state(protocol.OpMow))
	lastIsTransit := func(p []string) bool { return strings.Contains(p[len(p)-1], `"transit"`) }
	waitUntil(lastIsTransit)
	cancel()
	<-done
	got := snapshot()
	if !strings.Contains(got[0], `"offline"`) || !lastIsTransit(got) || len(got) > 3 {
		t.Errorf("published = %q", got)
	}
	for i := 1; i < len(got); i++ {
		if got[i] == got[i-1] {
			t.Errorf("published the same state twice: %q", got[i])
		}
	}
}

func TestErrorStatus(t *testing.T) {
	tests := []struct {
		err  error
		want int
	}{
		{fmt.Errorf("x: %w", robot.ErrBusy), http.StatusConflict},
		{fmt.Errorf("x: %w", link.ErrOffline), http.StatusServiceUnavailable},
		{context.DeadlineExceeded, http.StatusGatewayTimeout},
		{robot.ErrMapCRCMismatch, http.StatusBadGateway},
	}
	for _, tt := range tests {
		if got := robot.ErrorStatus(tt.err); got != tt.want {
			t.Errorf("ErrorStatus(%v) = %d, want %d", tt.err, got, tt.want)
		}
	}
}
