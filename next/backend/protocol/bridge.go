package protocol

import (
	"encoding/json"
	"fmt"
	"strings"
)

// The MQTT bridge used with legacy CaSSAndRA publishes the robot data as
// JSON on <mower>/state, <mower>/stats and <mower>/props, and "true"/"false"
// on <mower>/online. Field names follow legacy sunraycommstack.py.

type bridgeState struct {
	BatteryVoltage *float64 `json:"battery_voltage"`
	Position       *struct {
		X                     *float64 `json:"x"`
		Y                     *float64 `json:"y"`
		Delta                 float64  `json:"delta"`
		Solution              int      `json:"solution"`
		MowPointIndex         int      `json:"mow_point_index"`
		Age                   float64  `json:"age"`
		Accuracy              float64  `json:"accuracy"`
		VisibleSatellites     int      `json:"visible_satellites"`
		VisibleSatellitesDGPS int      `json:"visible_satellites_dgps"`
	} `json:"position"`
	Job    *int `json:"job"`
	Sensor int  `json:"sensor"`
	Target struct {
		X float64 `json:"x"`
		Y float64 `json:"y"`
	} `json:"target"`
	Amps   float64 `json:"amps"`
	MapCRC int64   `json:"map_crc"`
}

// ParseBridgeState parses the JSON on <mower>/state. Battery voltage,
// position and job are required; everything else defaults to zero.
func ParseBridgeState(data []byte) (State, error) {
	var b bridgeState
	if err := json.Unmarshal(data, &b); err != nil {
		return State{}, fmt.Errorf("%w: bridge state: %w", ErrMalformed, err)
	}
	if b.BatteryVoltage == nil || b.Position == nil || b.Position.X == nil || b.Position.Y == nil || b.Job == nil {
		return State{}, fmt.Errorf("%w: bridge state lacks battery_voltage, position or job", ErrMalformed)
	}
	p := b.Position
	return State{
		BatteryVoltage:   *b.BatteryVoltage,
		X:                *p.X,
		Y:                *p.Y,
		HeadingRad:       p.Delta,
		Solution:         Solution(p.Solution),
		Op:               Op(*b.Job),
		MowPointIndex:    p.MowPointIndex,
		DGPSAgeSec:       p.Age,
		Sensor:           Sensor(b.Sensor),
		TargetX:          b.Target.X,
		TargetY:          b.Target.Y,
		AccuracyM:        p.Accuracy,
		Satellites:       p.VisibleSatellites,
		Amps:             b.Amps,
		SatellitesDGPS:   p.VisibleSatellitesDGPS,
		MapCRC:           b.MapCRC,
		TimetableWeekday: -1, // not sent by the bridge
	}, nil
}

type bridgeStats struct {
	DurationIdle             int     `json:"duration_idle"`
	DurationCharge           int     `json:"duration_charge"`
	DurationMow              int     `json:"duration_mow"`
	DurationMowInvalid       int     `json:"duration_mow_invalid"`
	DurationMowFloat         int     `json:"duration_mow_float"`
	DurationMowFix           int     `json:"duration_mow_fix"`
	DistanceMowTraveled      float64 `json:"distance_mow_traveled"`
	CounterGPSChkSumErrors   int     `json:"counter_gps_chk_sum_errors"`
	CounterDGPSChkSumErrors  int     `json:"counter_dgps_chk_sum_errors"`
	CounterInvalidRecoveries int     `json:"counter_invalid_recoveries"`
	CounterFloatRecoveries   int     `json:"counter_float_recoveries"`
	CounterGPSJumps          int     `json:"counter_gps_jumps"`
	CounterGPSMotionTimeout  int     `json:"counter_gps_motion_timeout"`
	CounterIMUTriggered      int     `json:"counter_imu_triggered"`
	CounterSonarTriggered    int     `json:"counter_sonar_triggered"`
	CounterBumperTriggered   int     `json:"counter_bumper_triggered"`
	CounterObstacles         int     `json:"counter_obstacles"`
	TimeMaxCycle             int     `json:"time_max_cycle"`
	TimeMaxDGPSAge           float64 `json:"time_max_dpgs_age"`
	SerialBufferSize         int     `json:"serial_buffer_size"`
	FreeMemory               int     `json:"free_memory"`
	ResetCause               int     `json:"reset_cause"`
	TempMin                  float64 `json:"temp_min"`
	TempMax                  float64 `json:"temp_max"`
}

// ParseBridgeStats parses the JSON on <mower>/stats. Counters the bridge
// does not send stay zero.
func ParseBridgeStats(data []byte) (Stats, error) {
	var b bridgeStats
	if err := json.Unmarshal(data, &b); err != nil {
		return Stats{}, fmt.Errorf("%w: bridge stats: %w", ErrMalformed, err)
	}
	return Stats{
		DurationIdleSec:       b.DurationIdle,
		DurationChargeSec:     b.DurationCharge,
		DurationMowSec:        b.DurationMow,
		DurationMowFloatSec:   b.DurationMowFloat,
		DurationMowFixSec:     b.DurationMowFix,
		FloatRecoveries:       b.CounterFloatRecoveries,
		DistanceMowTraveledM:  b.DistanceMowTraveled,
		MaxDGPSAgeSec:         b.TimeMaxDGPSAge,
		IMURecoveries:         b.CounterIMUTriggered,
		TempMinC:              b.TempMin,
		TempMaxC:              b.TempMax,
		GPSChecksumErrors:     b.CounterGPSChkSumErrors,
		DGPSChecksumErrors:    b.CounterDGPSChkSumErrors,
		MaxCycleTimeMs:        b.TimeMaxCycle,
		SerialBufferSize:      b.SerialBufferSize,
		DurationMowInvalidSec: b.DurationMowInvalid,
		InvalidRecoveries:     b.CounterInvalidRecoveries,
		Obstacles:             b.CounterObstacles,
		FreeMemory:            b.FreeMemory,
		ResetCause:            b.ResetCause,
		GPSJumps:              b.CounterGPSJumps,
		SonarTriggered:        b.CounterSonarTriggered,
		BumperTriggered:       b.CounterBumperTriggered,
		GPSMotionTimeouts:     b.CounterGPSMotionTimeout,
	}, nil
}

// ParseBridgeProps parses the JSON on <mower>/props.
func ParseBridgeProps(data []byte) (Version, error) {
	var b struct {
		Firmware string `json:"firmware"`
		Version  string `json:"version"`
	}
	if err := json.Unmarshal(data, &b); err != nil {
		return Version{}, fmt.Errorf("%w: bridge props: %w", ErrMalformed, err)
	}
	return Version{Firmware: b.Firmware, Version: b.Version}, nil
}

// ParseBridgeOnline parses <mower>/online. Like legacy, any payload
// containing "true" or "false" counts.
func ParseBridgeOnline(data []byte) (bool, error) {
	s := strings.ToLower(string(data))
	switch {
	case strings.Contains(s, "true"):
		return true, nil
	case strings.Contains(s, "false"):
		return false, nil
	}
	return false, fmt.Errorf("%w: bridge online %q", ErrMalformed, data)
}
