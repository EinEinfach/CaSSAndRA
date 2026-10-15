package app_test

import (
	"net/http"
	"path/filepath"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/app"
	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func TestRunWithHTTPLink(t *testing.T) {
	simCfg := link.DefaultSimConfig()
	simCfg.Password = 4711
	sim := link.NewSim(simCfg)
	robotSrv := testkit.RobotHTTPServer(t, sim)

	cfg := testConfig(t)
	writeSettings(t, cfg, func(s *settings.Settings) {
		s.Connection.Kind, s.Connection.HTTPURL, s.Connection.HTTPPassword = settings.LinkHTTP, robotSrv.URL, 4711
	})
	r := startWith(t, cfg)

	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusIdle })
	// The command gets through the encrypted link; without an uploaded dock
	// path the simulated robot then reports an error, as the firmware does.
	if code := post(t, r.baseURL+"/api/robot/dock"); code != http.StatusNoContent {
		t.Fatalf("POST dock = %d, want 204", code)
	}
	if op := sim.State().Op; op != protocol.OpError {
		t.Errorf("simulator op = %v, want error (dock without dock path)", op)
	}
}

func TestRunWithMQTTLink(t *testing.T) {
	broker := testkit.StartBroker(t, "127.0.0.1:0")
	commands := broker.Collect(t, "garden/alfred/command")

	cfg := testConfig(t)
	cfg.Poll.ReconnectDelay = 50 * time.Millisecond
	writeSettings(t, cfg, func(s *settings.Settings) {
		s.Connection.Kind, s.Connection.MQTTBroker = settings.LinkMQTT, broker.URL()
		s.Connection.MQTTClientID, s.Connection.MQTTMower = "cassandra-app-test", "garden/alfred"
	})
	r := startWith(t, cfg)

	state := `{"battery_voltage":27,"position":{"x":1,"y":2,"solution":2},"job":0}`
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		broker.Publish(t, "garden/alfred/state", state)
		var s robot.StateJSON
		if getJSON(r.baseURL+"/api/robot/state", &s) == nil && s.Status == robot.StatusIdle {
			break
		}
		time.Sleep(20 * time.Millisecond)
	}
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusIdle && s.Position.X == 1 })

	if code := post(t, r.baseURL+"/api/robot/dock"); code != http.StatusNoContent {
		t.Fatalf("POST dock = %d", code)
	}
	deadline = time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		for _, c := range commands() {
			if c == protocol.Dock().Encode() {
				return
			}
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Errorf("dock command not published; got %q", commands())
}

func TestRunWithMissingSerialPort(t *testing.T) {
	cfg := testConfig(t)
	writeSettings(t, cfg, func(s *settings.Settings) {
		s.Connection.Kind, s.Connection.UARTPort = settings.LinkUART, "/dev/cassandra-does-not-exist"
	})
	r := startWith(t, cfg)

	// The server keeps running and reports the robot offline.
	s := waitForRobot(t, r.baseURL, func(robot.StateJSON) bool { return true })
	if s.Status != robot.StatusOffline {
		t.Errorf("status = %q, want offline", s.Status)
	}
	if code := post(t, r.baseURL+"/api/robot/dock"); code != http.StatusServiceUnavailable {
		t.Errorf("POST dock = %d, want 503", code)
	}
}

// writeSettings stores the default settings changed by change in the data
// directory of cfg, as the UI would.
func writeSettings(t *testing.T, cfg app.Config, change func(s *settings.Settings)) {
	t.Helper()
	store, err := settings.Open(filepath.Join(cfg.DataDir, "settings.json"))
	if err != nil {
		t.Fatal(err)
	}
	s := settings.Default()
	change(&s)
	if err := store.Set(s); err != nil {
		t.Fatal(err)
	}
}
