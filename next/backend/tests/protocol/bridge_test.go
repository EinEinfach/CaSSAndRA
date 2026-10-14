package protocol_test

import (
	"errors"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// Payloads in the format legacy CaSSAndRA reads (sunraycommstack.py).
const bridgeStateJSON = `{
	"battery_voltage": 27.3,
	"position": {"x": -3.25, "y": 12.8, "delta": 1.57, "solution": 2, "mow_point_index": 153,
		"age": 0.65, "accuracy": 0.02, "visible_satellites": 28, "visible_satellites_dgps": 3},
	"job": 1, "sensor": 0, "target": {"x": -2.95, "y": 13.1}, "amps": 0.68, "map_crc": 123456
}`

func TestParseBridgeState(t *testing.T) {
	got, err := protocol.ParseBridgeState([]byte(bridgeStateJSON))
	if err != nil {
		t.Fatal(err)
	}
	want := protocol.State{
		BatteryVoltage: 27.3, X: -3.25, Y: 12.8, HeadingRad: 1.57, Solution: protocol.SolutionFix,
		Op: protocol.OpMow, MowPointIndex: 153, DGPSAgeSec: 0.65, TargetX: -2.95, TargetY: 13.1,
		AccuracyM: 0.02, Satellites: 28, Amps: 0.68, SatellitesDGPS: 3, MapCRC: 123456, TimetableWeekday: -1,
	}
	if got != want {
		t.Errorf("got  %+v\nwant %+v", got, want)
	}
}

func TestParseBridgeStateRejectsIncompleteData(t *testing.T) {
	for _, payload := range []string{
		`not json`,
		`{}`,
		`{"battery_voltage": 27, "job": 1}`,
		`{"battery_voltage": 27, "position": {"x": 1}, "job": 1}`,
		`{"position": {"x": 1, "y": 2}, "job": 1}`,
		`{"battery_voltage": 27, "position": {"x": 1, "y": 2}}`,
		`{"battery_voltage": "full", "position": {"x": 1, "y": 2}, "job": 1}`,
	} {
		if _, err := protocol.ParseBridgeState([]byte(payload)); !errors.Is(err, protocol.ErrMalformed) {
			t.Errorf("ParseBridgeState(%s) err = %v, want ErrMalformed", payload, err)
		}
	}
}

func TestParseBridgeStats(t *testing.T) {
	got, err := protocol.ParseBridgeStats([]byte(`{
		"duration_idle": 1, "duration_charge": 2, "duration_mow": 3, "duration_mow_invalid": 4,
		"duration_mow_float": 5, "duration_mow_fix": 6, "distance_mow_traveled": 7.5,
		"counter_gps_chk_sum_errors": 8, "counter_dgps_chk_sum_errors": 9, "counter_invalid_recoveries": 10,
		"counter_float_recoveries": 11, "counter_gps_jumps": 12, "counter_gps_motion_timeout": 13,
		"counter_imu_triggered": 14, "counter_sonar_triggered": 15, "counter_bumper_triggered": 16,
		"counter_obstacles": 17, "time_max_cycle": 18, "time_max_dpgs_age": 19.5, "serial_buffer_size": 20,
		"free_memory": 21, "reset_cause": 22, "temp_min": 8.5, "temp_max": 42.1, "unknown_field": 1
	}`))
	if err != nil {
		t.Fatal(err)
	}
	want := protocol.Stats{
		DurationIdleSec: 1, DurationChargeSec: 2, DurationMowSec: 3, DurationMowInvalidSec: 4,
		DurationMowFloatSec: 5, DurationMowFixSec: 6, DistanceMowTraveledM: 7.5, GPSChecksumErrors: 8,
		DGPSChecksumErrors: 9, InvalidRecoveries: 10, FloatRecoveries: 11, GPSJumps: 12, GPSMotionTimeouts: 13,
		IMURecoveries: 14, SonarTriggered: 15, BumperTriggered: 16, Obstacles: 17, MaxCycleTimeMs: 18,
		MaxDGPSAgeSec: 19.5, SerialBufferSize: 20, FreeMemory: 21, ResetCause: 22, TempMinC: 8.5, TempMaxC: 42.1,
	}
	if got != want {
		t.Errorf("got  %+v\nwant %+v", got, want)
	}
	if _, err := protocol.ParseBridgeStats([]byte(`[1,2]`)); !errors.Is(err, protocol.ErrMalformed) {
		t.Errorf("array err = %v, want ErrMalformed", err)
	}
}

func TestParseBridgeProps(t *testing.T) {
	got, err := protocol.ParseBridgeProps([]byte(`{"firmware": "Sunray", "version": "1.0.332"}`))
	if err != nil || got != (protocol.Version{Firmware: "Sunray", Version: "1.0.332"}) {
		t.Errorf("got %+v, %v", got, err)
	}
	if _, err := protocol.ParseBridgeProps([]byte(`{`)); !errors.Is(err, protocol.ErrMalformed) {
		t.Errorf("err = %v, want ErrMalformed", err)
	}
}

func TestParseBridgeOnline(t *testing.T) {
	tests := []struct {
		payload string
		want    bool
		ok      bool
	}{
		{"true", true, true},
		{"false", false, true},
		{`"True"`, true, true},
		{"online: false", false, true},
		{"maybe", false, false},
		{"", false, false},
	}
	for _, tt := range tests {
		got, err := protocol.ParseBridgeOnline([]byte(tt.payload))
		if (err == nil) != tt.ok || got != tt.want {
			t.Errorf("ParseBridgeOnline(%q) = %v, %v", tt.payload, got, err)
		}
	}
}
