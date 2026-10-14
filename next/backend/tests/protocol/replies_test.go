package protocol_test

import (
	"errors"
	"math"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

func TestParseVersion(t *testing.T) {
	tests := []struct {
		golden string
		want   protocol.Version
	}{
		{"version_current", protocol.Version{
			Firmware: "Sunray", Version: "1.0.332", Encrypted: true, Challenge: 57,
			Board: "Linux", Driver: "SR", MCUFirmware: "RM18", MCUFirmwareVers: "1.1.16", RobotID: "0123abcd",
		}},
		{"version_old", protocol.Version{Firmware: "Ardumower Sunray", Version: "1.0.219"}},
		{"version_real_sunray_1_0_324_sim", protocol.Version{
			Firmware: "Sunray", Version: "1.0.324", Board: "Linux", Driver: "XX",
			MCUFirmware: "XX", MCUFirmwareVers: "XX", RobotID: "sim",
		}},
	}
	for _, tt := range tests {
		t.Run(tt.golden, func(t *testing.T) {
			got, err := protocol.ParseVersion(payload(t, tt.golden))
			if err != nil {
				t.Fatal(err)
			}
			if got != tt.want {
				t.Errorf("got  %+v\nwant %+v", got, tt.want)
			}
		})
	}
}

var mowingState = protocol.State{
	BatteryVoltage: 27.52, X: -3.25, Y: 12.80, HeadingRad: 1.57,
	Solution: protocol.SolutionFix, Op: protocol.OpMow, MowPointIndex: 153, DGPSAgeSec: 0.65,
	Sensor: 0, TargetX: -2.95, TargetY: 13.10, AccuracyM: 0.02, Satellites: 28, Amps: 0.68,
	SatellitesDGPS: 0, MapCRC: 123456, LateralErrorM: 0.03, TimetableWeekday: 3, TimetableHour: 22,
}

func TestParseState(t *testing.T) {
	charging := mowingState
	charging.BatteryVoltage, charging.X, charging.Y, charging.HeadingRad = 28.10, 0, 0, 0
	charging.Op, charging.MowPointIndex, charging.DGPSAgeSec = protocol.OpCharge, 0, 1.20
	charging.TargetX, charging.TargetY, charging.Satellites, charging.Amps = 0, 0, 27, -1.25
	charging.LateralErrorM, charging.TimetableWeekday, charging.TimetableHour = 0, 5, 8

	chargingNegativeBoard := charging
	chargingNegativeBoard.Amps = -0.80

	// Firmware before timetable support: no timetable fields.
	fw300 := mowingState
	fw300.Solution, fw300.AccuracyM, fw300.Satellites = protocol.SolutionFloat, 0.12, 22
	fw300.TimetableWeekday, fw300.TimetableHour = -1, 0

	// Firmware before 1.0.264: no lateral error either.
	fw250 := fw300
	fw250.LateralErrorM = 0

	// Captured from Sunray 1.0.324 in Linux simulation mode.
	realSim := protocol.State{
		BatteryVoltage: 27, X: -4.71, Y: -36.98, HeadingRad: -1.55,
		Solution: protocol.SolutionFix, Op: protocol.OpIdle, MowPointIndex: 2,
		TargetX: -4.90, TargetY: -36.87, AccuracyM: 0.01, MapCRC: -904911, LateralErrorM: -0.01,
		TimetableWeekday: -1,
	}

	tests := []struct {
		golden string
		want   protocol.State
	}{
		{"state_mowing", mowingState},
		{"state_charging", charging},
		{"state_charging_negative_board_current", chargingNegativeBoard},
		{"state_fw_1_0_300", fw300},
		{"state_fw_1_0_250", fw250},
		{"state_real_sunray_1_0_324_sim", realSim},
	}
	for _, tt := range tests {
		t.Run(tt.golden, func(t *testing.T) {
			got, err := protocol.ParseState(payload(t, tt.golden))
			if err != nil {
				t.Fatal(err)
			}
			if got != tt.want {
				t.Errorf("got  %+v\nwant %+v", got, tt.want)
			}
		})
	}
}

func TestParseStateWithNaNAndNegativeCRC(t *testing.T) {
	got, err := protocol.ParseState(payload(t, "state_idle_gps_invalid"))
	if err != nil {
		t.Fatal(err)
	}
	if !math.IsNaN(got.DGPSAgeSec) || !math.IsNaN(got.AccuracyM) {
		t.Errorf("DGPSAgeSec = %v, AccuracyM = %v, want NaN", got.DGPSAgeSec, got.AccuracyM)
	}
	if got.Solution != protocol.SolutionInvalid || got.Op != protocol.OpIdle {
		t.Errorf("Solution = %v, Op = %v, want invalid, idle", got.Solution, got.Op)
	}
	if got.Sensor.String() != "gps invalid" {
		t.Errorf("Sensor = %q, want gps invalid", got.Sensor)
	}
	if got.MapCRC != -4711 || got.TimetableWeekday != -1 {
		t.Errorf("MapCRC = %d, TimetableWeekday = %d, want -4711, -1", got.MapCRC, got.TimetableWeekday)
	}
}

func TestParseStateIgnoresFieldsFromNewerFirmware(t *testing.T) {
	newer := payload(t, "state_mowing") + ",99,1.5"
	got, err := protocol.ParseState(newer)
	if err != nil {
		t.Fatal(err)
	}
	if got != mowingState {
		t.Errorf("got  %+v\nwant %+v", got, mowingState)
	}
}

var currentStats = protocol.Stats{
	DurationIdleSec: 3600, DurationChargeSec: 7200, DurationMowSec: 5400, DurationMowFloatSec: 600,
	DurationMowFixSec: 4700, FloatRecoveries: 3, DistanceMowTraveledM: 1234.50, MaxDGPSAgeSec: 12.30,
	IMURecoveries: 1, TempMinC: 8.50, TempMaxC: 42.10, GPSChecksumErrors: 2, DGPSChecksumErrors: 5,
	MaxCycleTimeSec: 0.15, SerialBufferSize: 1024, DurationMowInvalidSec: 100, InvalidRecoveries: 4,
	Obstacles: 17, FreeMemory: 52000, ResetCause: 4, GPSJumps: 1, SonarTriggered: 6, BumperTriggered: 9,
	GPSMotionTimeouts: 2, DurationMowMotorRecoverySec: 30, LiftTriggered: 1, GPSNoSpeedTriggered: 2,
	ToFTriggered: 3, DiffIMUWheelYawSpeedTriggered: 4, IMUNoRotationTriggered: 5, RotationTimeoutTriggered: 6,
}

func TestParseStats(t *testing.T) {
	fw25 := currentStats
	fw25.LiftTriggered, fw25.GPSNoSpeedTriggered, fw25.ToFTriggered = 0, 0, 0
	fw25.DiffIMUWheelYawSpeedTriggered, fw25.IMUNoRotationTriggered, fw25.RotationTimeoutTriggered = 0, 0, 0

	fw24 := fw25
	fw24.DurationMowMotorRecoverySec = 0

	// Captured from Sunray 1.0.324 in Linux simulation mode.
	realSim := protocol.Stats{
		DurationIdleSec: 127, DurationMowSec: 23, DurationMowFixSec: 23, MaxDGPSAgeSec: 0.20,
		TempMinC: 50, TempMaxC: 50, MaxCycleTimeSec: 0.03, SerialBufferSize: 4096,
		InvalidRecoveries: 1, FreeMemory: 1000000, GPSJumps: 1,
	}

	tests := []struct {
		golden string
		want   protocol.Stats
	}{
		{"stats_current", currentStats},
		{"stats_fw_25_fields", fw25},
		{"stats_fw_24_fields", fw24},
		{"stats_real_sunray_1_0_324_sim", realSim},
	}
	for _, tt := range tests {
		t.Run(tt.golden, func(t *testing.T) {
			got, err := protocol.ParseStats(payload(t, tt.golden))
			if err != nil {
				t.Fatal(err)
			}
			if got != tt.want {
				t.Errorf("got  %+v\nwant %+v", got, tt.want)
			}
		})
	}
}

func TestParseObstacles(t *testing.T) {
	got, err := protocol.ParseObstacles(payload(t, "obstacles_two"))
	if err != nil {
		t.Fatal(err)
	}
	want := [][]geo.Point{
		pts(1, 1, 1.5, 1, 1.5, 1.5, 1, 1.5),
		pts(-2, 0, -1.5, 0.5, -2.5, 0.5),
	}
	if len(got) != len(want) {
		t.Fatalf("got %d obstacles, want %d", len(got), len(want))
	}
	for i := range want {
		if len(got[i]) != len(want[i]) {
			t.Fatalf("obstacle %d has %d points, want %d", i, len(got[i]), len(want[i]))
		}
		for j := range want[i] {
			if got[i][j] != want[i][j] {
				t.Errorf("obstacle %d point %d = %v, want %v", i, j, got[i][j], want[i][j])
			}
		}
	}
}

func TestParseObstaclesNone(t *testing.T) {
	for _, golden := range []string{"obstacles_none", "obstacles_real_sunray_1_0_324_sim"} {
		t.Run(golden, func(t *testing.T) {
			got, err := protocol.ParseObstacles(payload(t, golden))
			if err != nil {
				t.Fatal(err)
			}
			if len(got) != 0 {
				t.Errorf("got %d obstacles, want 0", len(got))
			}
		})
	}
}

func TestParseWaypointAck(t *testing.T) {
	got, err := protocol.ParseWaypointAck(payload(t, "ack_waypoints"))
	if err != nil {
		t.Fatal(err)
	}
	if got != 30 {
		t.Errorf("next index = %d, want 30", got)
	}
}

func TestGoldenAcksMatchTheirRequests(t *testing.T) {
	tests := []struct{ request, golden string }{
		{protocol.Stop().Encode(), "ack_control"},
		{"AT+W,0,1,2", "ack_waypoints"},
		{"AT+N,4,0,0,1,0", "ack_waycount"},
		{"AT+X,0,3,4", "ack_exclusions"},
		{protocol.RequestState, "state_mowing"},
		{protocol.RequestObstacles, "obstacles_two"},
	}
	for _, tt := range tests {
		if !protocol.ReplyMatches(tt.request, payload(t, tt.golden)) {
			t.Errorf("%s does not match request %q", tt.golden, tt.request)
		}
	}
}

func TestParseRejectsMalformedReplies(t *testing.T) {
	parsers := map[string]func(string) error{
		"version":   func(p string) error { _, err := protocol.ParseVersion(p); return err },
		"state":     func(p string) error { _, err := protocol.ParseState(p); return err },
		"stats":     func(p string) error { _, err := protocol.ParseStats(p); return err },
		"obstacles": func(p string) error { _, err := protocol.ParseObstacles(p); return err },
		"waypoint":  func(p string) error { _, err := protocol.ParseWaypointAck(p); return err },
	}
	tests := []struct{ parser, payload string }{
		{"version", "S,1,2,3,4"},
		{"version", "V,Sunray,1.0.332,1"},
		{"version", "V,Sunray,1.0.332,x,57"},
		{"state", "V,Sunray,1.0.332,0,0"},
		{"state", "S,27.5,1,2"},
		{"state", "S,27.5,abc,12.8,1.57,2,1,153,0.65,0,-2.95,13.10,0.02,28,0.68,0,123456"},
		{"stats", "T,1,2,3"},
		{"stats", "S,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24"},
		{"obstacles", "S2"},
		{"obstacles", "S2,x"},
		{"obstacles", "S2,1,0.5,0.5,1"},
		{"obstacles", "S2,1,0.5,0.5,1,3,1,1,2,2"},
		{"obstacles", "S2,2,0.5,0.5,1,1,1,1"},
		{"obstacles", "S2,1,0.5,0.5,1,-1"},
		{"obstacles", "S2,1,0.5,0.5,1,1,1,y"},
		{"obstacles", "S2,-1"},
		{"obstacles", "S2,2,0.5,0.5,1,1,1,1,0.5,0.5,1"},
		{"obstacles", "S2,1,0.5,0.5,1,1E19"},
		{"state", "S,27.5,1,2,1.5,2,1E10,153,0.65,0,-2.95,13.10,0.02,28,0.68,0,123456"},
		{"obstacles", "S2,99999999999,0.5,0.5,1,0"},
		{"waypoint", "W"},
		{"waypoint", "W,abc"},
		{"waypoint", "C"},
	}
	for _, tt := range tests {
		if err := parsers[tt.parser](tt.payload); !errors.Is(err, protocol.ErrMalformed) {
			t.Errorf("%s(%q) err = %v, want ErrMalformed", tt.parser, tt.payload, err)
		}
	}
}

func TestEnumStrings(t *testing.T) {
	tests := []struct{ got, want string }{
		{protocol.SolutionInvalid.String(), "invalid"},
		{protocol.SolutionFloat.String(), "float"},
		{protocol.SolutionFix.String(), "fix"},
		{protocol.Solution(7).String(), "solution(7)"},
		{protocol.Sensor(0).String(), "none"},
		{protocol.Sensor(18).String(), "temperature out of range"},
		{protocol.Sensor(19).String(), "sensor(19)"},
		{protocol.Sensor(-1).String(), "sensor(-1)"},
	}
	for _, tt := range tests {
		if tt.got != tt.want {
			t.Errorf("got %q, want %q", tt.got, tt.want)
		}
	}
}

func TestParseStateTreatsNaNIntegersAsZero(t *testing.T) {
	got, err := protocol.ParseState("S,27.5,1,2,1.5,2,1,nan,0.65,0,-2.95,13.10,0.02,nan,0.68,0,123456")
	if err != nil {
		t.Fatal(err)
	}
	if got.MowPointIndex != 0 || got.Satellites != 0 {
		t.Errorf("MowPointIndex = %d, Satellites = %d, want 0, 0", got.MowPointIndex, got.Satellites)
	}
}
