package mqttapi_test

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"os"
	"slices"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/mqttapi"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
)

func mowing() robot.Snapshot {
	return robot.Snapshot{
		Status: robot.StatusMow, Online: true, Firmware: "Sunray", FirmwareVersion: "1.0.331",
		Position: geo.Point{X: 12.3456, Y: -3}, Target: geo.Point{X: 14, Y: -2.5}, HeadingRad: 1.25,
		BatteryV: 27.0, SoCPercent: 85, Amps: 0.567, Solution: protocol.SolutionFix,
		Satellites: 28, SatellitesDGPS: 21, DGPSAgeSec: 0.6, Op: protocol.OpMow, MowPointIndex: 120,
		MowMotorOn: true, UpdatedAt: t0,
	}
}

func topic(t *testing.T, msgs []mqttapi.Message, name string) []byte {
	t.Helper()
	for _, m := range msgs {
		if m.Topic == name {
			return m.Payload
		}
	}
	t.Fatalf("no %s topic in %v", name, msgs)
	return nil
}

// The expected payload is written by hand after legacy robottopic.py: the
// same keys in the same order, floats with a decimal point.
func TestRobotTopicIsLikeLegacy(t *testing.T) {
	want, err := os.ReadFile("testdata/robot.json")
	if err != nil {
		t.Fatal(err)
	}
	r := &fakeRobot{snap: mowing()}
	api := mqttapi.New(r, &fakeTasks{r}, mqttapi.Config{Version: "test"})
	got := topic(t, api.State(), "robot")
	if !bytes.Equal(got, bytes.TrimSpace(want)) {
		t.Errorf("robot topic\n got %s\nwant %s", got, bytes.TrimSpace(want))
	}
	if string(topic(t, api.State(), "status")) != "ready" {
		t.Error("status is not ready")
	}
}

func robotJSON(t *testing.T, api *mqttapi.API) mqttapi.RobotJSON {
	t.Helper()
	var r mqttapi.RobotJSON
	if err := json.Unmarshal(topic(t, api.State(), "robot"), &r); err != nil {
		t.Fatal(err)
	}
	return r
}

func TestRobotTopicTexts(t *testing.T) {
	tests := []struct {
		name              string
		change            func(s *robot.Snapshot)
		sensor, dock, age string
		solution          string
	}{
		{"error names the sensor like legacy", func(s *robot.Snapshot) {
			s.Op, s.Status, s.Sensor = protocol.OpError, robot.StatusError, 13
		}, "bumper error", "", "0.6s", "fix"},
		{"docking shows the reason", func(s *robot.Snapshot) {
			s.Op, s.Status, s.DockReason = protocol.OpDock, robot.StatusDocking, robot.DockReasonUser
		}, "operator", "operator", "0.6s", "fix"},
		{"schedule", func(s *robot.Snapshot) { s.DockReason = robot.DockReasonSchedule }, "schedule", "schedule", "0.6s", "fix"},
		{"old corrections", func(s *robot.Snapshot) { s.DGPSAgeSec, s.Solution = 7300, protocol.SolutionFloat }, ".", "", "2h", "float"},
		{"no corrections", func(s *robot.Snapshot) { s.DGPSAgeSec, s.Solution = 400000, protocol.SolutionInvalid }, ".", "", "99+d", "invalid"},
		{"whole seconds", func(s *robot.Snapshot) { s.DGPSAgeSec = 2 }, ".", "", "2.0s", "fix"},
		{"minutes", func(s *robot.Snapshot) { s.DGPSAgeSec = 125 }, ".", "", "2min", "fix"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := mowing()
			tt.change(&s)
			r := &fakeRobot{snap: s}
			got := robotJSON(t, mqttapi.New(r, &fakeTasks{r}, mqttapi.Config{}))
			dock := ""
			if got.DockReason != nil {
				dock = *got.DockReason
			}
			if got.SensorState != tt.sensor || dock != tt.dock || got.GPS.Age != tt.age || got.GPS.Solution != tt.solution {
				t.Errorf("sensor %q dock %q age %q solution %q; want %q %q %q %q",
					got.SensorState, dock, got.GPS.Age, got.GPS.Solution, tt.sensor, tt.dock, tt.age, tt.solution)
			}
		})
	}
}

func TestRobotTopicMeasuresSpeedAndTimePerPoint(t *testing.T) {
	r := &fakeRobot{snap: mowing()}
	api := mqttapi.New(r, &fakeTasks{r}, mqttapi.Config{})
	api.State()
	r.set(func(s *robot.Snapshot) {
		s.UpdatedAt = t0.Add(2 * time.Second)
		s.Position.X += 0.6 // 0.3 m/s
	})
	got := robotJSON(t, api)
	if got.Speed != 0.3 || got.AverageSpeed <= 0 {
		t.Errorf("speed %v, average %v; want 0.3 and above 0", got.Speed, got.AverageSpeed)
	}
	r.set(func(s *robot.Snapshot) {
		s.UpdatedAt = t0.Add(12 * time.Second)
		s.MowPointIndex += 5
	})
	got = robotJSON(t, api)
	if got.SecondsPerIdx == nil || *got.SecondsPerIdx != 2.4 {
		t.Errorf("seconds per point = %v, want 12 s / 5 points", got.SecondsPerIdx)
	}
	if got.SensorState == "." {
		t.Error("the sensor dots do not move on")
	}
	r.set(func(s *robot.Snapshot) {
		s.UpdatedAt = t0.Add(14 * time.Second)
		s.Op, s.Status = protocol.OpIdle, robot.StatusIdle
	})
	if got := robotJSON(t, api); got.Speed != 0 {
		t.Errorf("speed while idle = %v", got.Speed)
	}
}

func TestRobotCommands(t *testing.T) {
	tests := []struct {
		cmd  string
		want string
	}{
		{`{"robot": {"command": "stop", "value": []}}`, "stop"},
		{`{"robot": {"command": "dock", "value": []}}`, "dock"},
		{`{"robot": {"command": "move", "value": [0.3, -0.5]}}`, "move 0.3 -0.5"},
		{`{"robot": {"command": "mow", "value": ["resume"]}}`, "mow"},
		{`{"robot": {"command": "goTo", "value": {"x": [3.5], "y": [-1.0]}}}`, "goto 3.5,-1.0"},
		{`{"robot": {"command": "reboot", "value": []}}`, "reboot"},
		{`{"robot": {"command": "rebootGps", "value": []}}`, "reboot gps"},
		{`{"robot": {"command": "shutdown", "value": []}}`, "shutdown"},
		{`{"robot": {"command": "setMowSpeed", "value": [0.4]}}`, "speed 0.4"},
		{`{"robot": {"command": "setGoToSpeed", "value": [0.6]}}`, "speed 0.6"},
		{`{"robot": {"command": "setMowProgress", "value": [0.25]}}`, "skip to 0.25"},
		{`{"robot": {"command": "toggleMowMotor", "value": []}}`, "mow motor off"},
		{`{"robot": {"command": "skipNextPoint", "value": []}}`, "skip next point"},
	}
	for _, tt := range tests {
		r := &fakeRobot{snap: mowing()}
		api := mqttapi.New(r, &fakeTasks{r}, mqttapi.Config{})
		if _, err := api.Handle(context.Background(), []byte(tt.cmd)); err != nil {
			t.Errorf("%s: %v", tt.cmd, err)
		}
		if got := r.recorded(); !slices.Equal(got, []string{tt.want}) {
			t.Errorf("%s: calls %v, want %q", tt.cmd, got, tt.want)
		}
	}
}

func TestInvalidCommandsSendNothing(t *testing.T) {
	tests := []struct {
		cmd  string
		want error
	}{
		{`not json`, mqttapi.ErrInvalid},
		{`{"robot": "stop"}`, mqttapi.ErrInvalid},
		{`{"robot": {"value": []}}`, mqttapi.ErrInvalid},
		{`{"robot": {"command": "move", "value": [0.3]}}`, mqttapi.ErrInvalid},
		{`{"robot": {"command": "goTo", "value": {"x": [1], "y": []}}}`, mqttapi.ErrInvalid},
		{`{"robot": {"command": "goTo", "value": {"x": [], "y": []}}}`, mqttapi.ErrInvalid},
		{`{"robot": {"command": "mow", "value": []}}`, mqttapi.ErrInvalid},
		{`{"robot": {"command": "mow", "value": ["everything"]}}`, mqttapi.ErrUnknown},
		{`{"robot": {"command": "fly", "value": []}}`, mqttapi.ErrUnknown},
		{`{"garden": {"command": "water", "value": []}}`, mqttapi.ErrUnknown},
	}
	for _, tt := range tests {
		r := &fakeRobot{snap: mowing()}
		api := mqttapi.New(r, &fakeTasks{r}, mqttapi.Config{})
		if _, err := api.Handle(context.Background(), []byte(tt.cmd)); !errors.Is(err, tt.want) {
			t.Errorf("%s: err = %v, want %v", tt.cmd, err, tt.want)
		}
		if got := r.recorded(); len(got) != 0 {
			t.Errorf("%s: sent %v", tt.cmd, got)
		}
	}
}
