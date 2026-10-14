package app_test

import (
	"context"
	"net"
	"net/http"
	"strings"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/app"
	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func TestRunWithHTTPLink(t *testing.T) {
	simCfg := link.DefaultSimConfig()
	simCfg.Password = 4711
	sim := link.NewSim(simCfg)
	robotSrv := testkit.RobotHTTPServer(t, sim)

	cfg := testConfig(t)
	cfg.Link = app.LinkConfig{Kind: app.LinkHTTP, HTTPURL: robotSrv.URL, HTTPPassword: 4711}
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
	cfg.Link = app.LinkConfig{Kind: app.LinkMQTT, MQTT: link.MQTTConfig{
		Broker: broker.URL(), ClientID: "cassandra-app-test", MowerName: "garden/alfred",
		ReconnectDelay: 50 * time.Millisecond,
	}}
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
	cfg.Link = app.LinkConfig{Kind: app.LinkUART, UARTPort: "/dev/cassandra-does-not-exist", UARTBaud: 115200}
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

func TestRunRejectsIncompleteLinkConfig(t *testing.T) {
	tests := []struct {
		name string
		link app.LinkConfig
		want string
	}{
		{"unknown kind", app.LinkConfig{Kind: "bluetooth"}, "unknown link"},
		{"http without URL", app.LinkConfig{Kind: app.LinkHTTP}, "robot URL"},
		{"uart without port", app.LinkConfig{Kind: app.LinkUART, UARTBaud: 115200}, "port"},
		{"uart without baud", app.LinkConfig{Kind: app.LinkUART, UARTPort: "/dev/x"}, "baud"},
		{"mqtt without broker", app.LinkConfig{Kind: app.LinkMQTT, MQTT: link.MQTTConfig{MowerName: "m"}}, "broker"},
		{"mqtt without mower", app.LinkConfig{Kind: app.LinkMQTT, MQTT: link.MQTTConfig{Broker: "tcp://x:1"}}, "mower"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ln, err := net.Listen("tcp", "127.0.0.1:0")
			if err != nil {
				t.Fatal(err)
			}
			defer func() { _ = ln.Close() }()
			cfg := testConfig(t)
			cfg.Link = tt.link
			err = app.Run(context.Background(), cfg, ln)
			if err == nil || !strings.Contains(err.Error(), tt.want) {
				t.Errorf("err = %v, want it to mention %q", err, tt.want)
			}
		})
	}
}
