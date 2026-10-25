package stats

import "github.com/EinEinfach/CaSSAndRA/next/backend/protocol"

// counter is one AT+T value that only grows until the robot restarts. The
// database keeps how much it grew per hour.
type counter struct {
	name   string // JSON name and database column
	column string
	get    func(s protocol.Stats) float64
}

// maximum is one AT+T value that is the maximum since the robot started.
// The database keeps the highest value per hour.
type maximum = counter

func i(v int) float64 { return float64(v) }

var counters = []counter{
	{"idleSec", "idle_sec", func(s protocol.Stats) float64 { return i(s.DurationIdleSec) }},
	{"chargeSec", "charge_sec", func(s protocol.Stats) float64 { return i(s.DurationChargeSec) }},
	{"mowSec", "mow_sec", func(s protocol.Stats) float64 { return i(s.DurationMowSec) }},
	{"mowFixSec", "mow_fix_sec", func(s protocol.Stats) float64 { return i(s.DurationMowFixSec) }},
	{"mowFloatSec", "mow_float_sec", func(s protocol.Stats) float64 { return i(s.DurationMowFloatSec) }},
	{"mowInvalidSec", "mow_invalid_sec", func(s protocol.Stats) float64 { return i(s.DurationMowInvalidSec) }},
	{"mowMotorRecoverySec", "mow_motor_recovery_sec", func(s protocol.Stats) float64 { return i(s.DurationMowMotorRecoverySec) }},
	{"distanceMowM", "distance_mow_m", func(s protocol.Stats) float64 { return s.DistanceMowTraveledM }},
	{"obstacles", "obstacles", func(s protocol.Stats) float64 { return i(s.Obstacles) }},
	{"bumper", "bumper", func(s protocol.Stats) float64 { return i(s.BumperTriggered) }},
	{"sonar", "sonar", func(s protocol.Stats) float64 { return i(s.SonarTriggered) }},
	{"lift", "lift", func(s protocol.Stats) float64 { return i(s.LiftTriggered) }},
	{"tof", "tof", func(s protocol.Stats) float64 { return i(s.ToFTriggered) }},
	{"rotationTimeouts", "rotation_timeouts", func(s protocol.Stats) float64 { return i(s.RotationTimeoutTriggered) }},
	{"imuNoRotation", "imu_no_rotation", func(s protocol.Stats) float64 { return i(s.IMUNoRotationTriggered) }},
	{"diffImuWheelYawSpeed", "diff_imu_wheel_yaw_speed", func(s protocol.Stats) float64 { return i(s.DiffIMUWheelYawSpeedTriggered) }},
	{"gpsMotionTimeouts", "gps_motion_timeouts", func(s protocol.Stats) float64 { return i(s.GPSMotionTimeouts) }},
	{"gpsNoSpeed", "gps_no_speed", func(s protocol.Stats) float64 { return i(s.GPSNoSpeedTriggered) }},
	{"gpsJumps", "gps_jumps", func(s protocol.Stats) float64 { return i(s.GPSJumps) }},
	{"floatRecoveries", "float_recoveries", func(s protocol.Stats) float64 { return i(s.FloatRecoveries) }},
	{"invalidRecoveries", "invalid_recoveries", func(s protocol.Stats) float64 { return i(s.InvalidRecoveries) }},
	{"imuRecoveries", "imu_recoveries", func(s protocol.Stats) float64 { return i(s.IMURecoveries) }},
	{"gpsChecksumErrors", "gps_checksum_errors", func(s protocol.Stats) float64 { return i(s.GPSChecksumErrors) }},
	{"dgpsChecksumErrors", "dgps_checksum_errors", func(s protocol.Stats) float64 { return i(s.DGPSChecksumErrors) }},
}

var maxima = []maximum{
	{"maxCycleTimeSec", "max_cycle_time_sec", func(s protocol.Stats) float64 { return s.MaxCycleTimeSec }},
	{"maxDgpsAgeSec", "max_dgps_age_sec", func(s protocol.Stats) float64 { return s.MaxDGPSAgeSec }},
}

// growth is how much c grew from old to now; a smaller value means the robot
// restarted and counts from zero again.
func growth(old, now float64) float64 {
	if now < old {
		return now
	}
	return now - old
}
