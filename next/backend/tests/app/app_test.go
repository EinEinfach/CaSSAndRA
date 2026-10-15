package app_test

import (
	"bufio"
	"context"
	"encoding/json"
	"net"
	"net/http"
	"strings"
	"testing"
	"testing/fstest"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/app"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/server"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func testConfig(t *testing.T) app.Config {
	t.Helper()
	cfg := app.DefaultConfig()
	cfg.Version = "test"
	cfg.UI = fstest.MapFS{"index.html": {Data: []byte("ui")}}
	cfg.Logger = testkit.Logger(t)
	cfg.DataDir = t.TempDir()
	cfg.SimTick = 10 * time.Millisecond
	cfg.Poll.StateInterval = 10 * time.Millisecond
	cfg.PublishInterval = 10 * time.Millisecond
	return cfg
}

type running struct {
	baseURL string
	cancel  context.CancelFunc
	done    <-chan struct{} // closed when Run returned
	err     *error          // Run's result, valid after done
}

func start(t *testing.T) running {
	t.Helper()
	return startWith(t, testConfig(t))
}

func startWith(t *testing.T, cfg app.Config) running {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	var runErr error
	go func() {
		runErr = app.Run(ctx, cfg, ln)
		close(done)
	}()
	t.Cleanup(func() {
		cancel()
		<-done
	})
	return running{baseURL: "http://" + ln.Addr().String(), cancel: cancel, done: done, err: &runErr}
}

func getJSON(url string, v any) error {
	res, err := http.Get(url)
	if err != nil {
		return err
	}
	defer func() { _ = res.Body.Close() }()
	return json.NewDecoder(res.Body).Decode(v)
}

func post(t *testing.T, url string) int {
	t.Helper()
	res, err := http.Post(url, "application/json", nil)
	if err != nil {
		t.Fatalf("POST %s: %v", url, err)
	}
	_ = res.Body.Close()
	return res.StatusCode
}

// waitForRobot polls the robot state until cond holds.
func waitForRobot(t *testing.T, baseURL string, cond func(robot.StateJSON) bool) robot.StateJSON {
	t.Helper()
	var s robot.StateJSON
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		if err := getJSON(baseURL+"/api/robot/state", &s); err == nil && cond(s) {
			return s
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("robot state never matched; last: %+v", s)
	return s
}

func TestRunServesHealth(t *testing.T) {
	r := start(t)
	var got server.Health
	deadline := time.Now().Add(2 * time.Second)
	for getJSON(r.baseURL+"/api/health", &got) != nil && time.Now().Before(deadline) {
		time.Sleep(5 * time.Millisecond)
	}
	if got.Version != "test" || got.Status != "ok" {
		t.Errorf("health = %+v", got)
	}
}

func TestRunConnectsTheSimulatorAndUploadsTheDemoMap(t *testing.T) {
	r := start(t)
	s := waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusIdle && s.MapCRC != 0 })
	if s.Firmware != "Sunray" || s.SoCPercent != 100 {
		t.Errorf("state = %+v", s)
	}
	var m robot.MapJSON
	if err := getJSON(r.baseURL+"/api/robot/map", &m); err != nil {
		t.Fatal(err)
	}
	if len(m.Perimeter) != 4 || len(m.Way) == 0 || len(m.Dock) != 2 {
		t.Errorf("map = %d perimeter, %d way, %d dock points", len(m.Perimeter), len(m.Way), len(m.Dock))
	}

	if code := post(t, r.baseURL+"/api/robot/mow"); code != http.StatusNoContent {
		t.Fatalf("POST mow = %d", code)
	}
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusMow })
	if code := post(t, r.baseURL+"/api/robot/stop"); code != http.StatusNoContent {
		t.Fatalf("POST stop = %d", code)
	}
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusIdle })
}

func TestRunStreamsRobotEvents(t *testing.T) {
	r := start(t)
	res, err := http.Get(r.baseURL + "/api/events")
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = res.Body.Close() }()
	if ct := res.Header.Get("Content-Type"); ct != "text/event-stream" {
		t.Fatalf("Content-Type = %q", ct)
	}

	lines := bufio.NewScanner(res.Body)
	deadline := time.Now().Add(5 * time.Second)
	for lines.Scan() && time.Now().Before(deadline) {
		data, ok := strings.CutPrefix(lines.Text(), "data: ")
		if !ok {
			continue
		}
		var s robot.StateJSON
		if err := json.Unmarshal([]byte(data), &s); err != nil {
			t.Fatalf("event data %q: %v", data, err)
		}
		if s.Status == robot.StatusIdle {
			return
		}
	}
	t.Fatal("no idle robot event received")
}

func TestShutdownWithOpenEventStream(t *testing.T) {
	r := start(t)
	res, err := http.Get(r.baseURL + "/api/events")
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = res.Body.Close() }()

	r.cancel()
	select {
	case <-r.done:
		if *r.err != nil {
			t.Fatalf("Run returned %v, want nil", *r.err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("shutdown blocked by the open event stream")
	}
}

func TestRunRejectsInvalidConfig(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = ln.Close() }()
	err = app.Run(context.Background(), app.Config{}, ln)
	if err == nil || !strings.Contains(err.Error(), "must be positive") {
		t.Errorf("Run with empty config err = %v, want validation error", err)
	}
	cfg := testConfig(t)
	cfg.DataDir = ""
	if err := app.Run(context.Background(), cfg, ln); err == nil || !strings.Contains(err.Error(), "DataDir") {
		t.Errorf("Run without DataDir err = %v, want validation error", err)
	}
}

func TestRunFailsOnClosedListener(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	_ = ln.Close()
	if err := app.Run(context.Background(), testConfig(t), ln); err == nil {
		t.Fatal("Run on a closed listener returned nil, want error")
	}
}
