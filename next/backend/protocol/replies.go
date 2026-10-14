package protocol

import (
	"fmt"
	"math"
	"strconv"
	"strings"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
)

// Version is the reply to AT+V. Fields after Challenge are missing on older
// firmware and stay empty.
type Version struct {
	Firmware        string // e.g. "Sunray"
	Version         string // e.g. "1.0.332"
	Encrypted       bool
	Challenge       int
	Board           string
	Driver          string // SR (serial robot), CR (CAN robot), AM (Ardumower)
	MCUFirmware     string
	MCUFirmwareVers string
	RobotID         string
}

// Solution is the GPS solution (SolType in the firmware).
type Solution int

const (
	SolutionInvalid Solution = iota
	SolutionFloat
	SolutionFix
)

func (s Solution) String() string {
	switch s {
	case SolutionInvalid:
		return "invalid"
	case SolutionFloat:
		return "float"
	case SolutionFix:
		return "fix"
	}
	return "solution(" + strconv.Itoa(int(s)) + ")"
}

// Sensor is the sensor/error state (Sensor in the firmware).
type Sensor int

var sensorNames = []string{
	"none", "battery undervoltage", "obstacle", "gps fix timeout", "imu timeout",
	"imu tilt", "kidnapped", "motor overload", "motor error", "gps invalid",
	"odometry error", "no map route", "memory overflow", "bumper", "sonar",
	"lift", "rain", "stop button", "temperature out of range",
}

func (s Sensor) String() string {
	if s >= 0 && int(s) < len(sensorNames) {
		return sensorNames[s]
	}
	return "sensor(" + strconv.Itoa(int(s)) + ")"
}

// State is the reply to AT+S. Fields after MapCRC are missing on older
// firmware: LateralError before 1.0.264, Timetable* before 1.0.3xx.
type State struct {
	BatteryVoltage float64
	X, Y           float64 // meters
	HeadingRad     float64
	Solution       Solution
	Op             Op
	MowPointIndex  int
	DGPSAgeSec     float64
	Sensor         Sensor
	TargetX        float64
	TargetY        float64
	AccuracyM      float64
	Satellites     int
	// Amps is the motor current, or the negative charging current while charging.
	Amps             float64
	SatellitesDGPS   int
	MapCRC           int64
	LateralErrorM    float64
	TimetableWeekday int // -1 if no timetable event is pending
	TimetableHour    int
}

// Stats is the reply to AT+T. Older firmware sends 24 or 25 fields; the
// missing counters stay zero.
type Stats struct {
	DurationIdleSec               int
	DurationChargeSec             int
	DurationMowSec                int
	DurationMowFloatSec           int
	DurationMowFixSec             int
	FloatRecoveries               int
	DistanceMowTraveledM          float64
	MaxDGPSAgeSec                 float64
	IMURecoveries                 int
	TempMinC                      float64
	TempMaxC                      float64
	GPSChecksumErrors             int
	DGPSChecksumErrors            int
	MaxCycleTimeSec               float64
	SerialBufferSize              int
	DurationMowInvalidSec         int
	InvalidRecoveries             int
	Obstacles                     int
	FreeMemory                    int
	ResetCause                    int
	GPSJumps                      int
	SonarTriggered                int
	BumperTriggered               int
	GPSMotionTimeouts             int
	DurationMowMotorRecoverySec   int
	LiftTriggered                 int
	GPSNoSpeedTriggered           int
	ToFTriggered                  int
	DiffIMUWheelYawSpeedTriggered int
	IMUNoRotationTriggered        int
	RotationTimeoutTriggered      int
}

// ParseVersion parses an AT+V reply payload ("V,...").
func ParseVersion(payload string) (Version, error) {
	f, err := fields(payload, "V", 4)
	if err != nil {
		return Version{}, err
	}
	p := parser{fields: f}
	v := Version{
		Firmware:  p.str(0),
		Version:   p.str(1),
		Encrypted: p.int(2) == 1,
		Challenge: p.int(3),
	}
	v.Board, v.Driver = p.str(4), p.str(5)
	v.MCUFirmware, v.MCUFirmwareVers, v.RobotID = p.str(6), p.str(7), p.str(8)
	return v, p.err("V")
}

// ParseState parses an AT+S reply payload ("S,...").
func ParseState(payload string) (State, error) {
	f, err := fields(payload, "S", 16)
	if err != nil {
		return State{}, err
	}
	p := parser{fields: f}
	s := State{
		BatteryVoltage:   p.float(0),
		X:                p.float(1),
		Y:                p.float(2),
		HeadingRad:       p.float(3),
		Solution:         Solution(p.int(4)),
		Op:               Op(p.int(5)),
		MowPointIndex:    p.int(6),
		DGPSAgeSec:       p.float(7),
		Sensor:           Sensor(p.int(8)),
		TargetX:          p.float(9),
		TargetY:          p.float(10),
		AccuracyM:        p.float(11),
		Satellites:       p.int(12),
		Amps:             p.amps(13),
		SatellitesDGPS:   p.int(14),
		MapCRC:           int64(p.float(15)),
		LateralErrorM:    p.float(16),
		TimetableWeekday: -1,
	}
	if len(f) > 18 {
		s.TimetableWeekday, s.TimetableHour = p.int(17), p.int(18)
	}
	return s, p.err("S")
}

// ParseStats parses an AT+T reply payload ("T,...").
func ParseStats(payload string) (Stats, error) {
	f, err := fields(payload, "T", 24)
	if err != nil {
		return Stats{}, err
	}
	p := parser{fields: f}
	s := Stats{
		DurationIdleSec:               p.int(0),
		DurationChargeSec:             p.int(1),
		DurationMowSec:                p.int(2),
		DurationMowFloatSec:           p.int(3),
		DurationMowFixSec:             p.int(4),
		FloatRecoveries:               p.int(5),
		DistanceMowTraveledM:          p.float(6),
		MaxDGPSAgeSec:                 p.float(7),
		IMURecoveries:                 p.int(8),
		TempMinC:                      p.float(9),
		TempMaxC:                      p.float(10),
		GPSChecksumErrors:             p.int(11),
		DGPSChecksumErrors:            p.int(12),
		MaxCycleTimeSec:               p.float(13),
		SerialBufferSize:              p.int(14),
		DurationMowInvalidSec:         p.int(15),
		InvalidRecoveries:             p.int(16),
		Obstacles:                     p.int(17),
		FreeMemory:                    p.int(18),
		ResetCause:                    p.int(19),
		GPSJumps:                      p.int(20),
		SonarTriggered:                p.int(21),
		BumperTriggered:               p.int(22),
		GPSMotionTimeouts:             p.int(23),
		DurationMowMotorRecoverySec:   p.int(24),
		LiftTriggered:                 p.int(25),
		GPSNoSpeedTriggered:           p.int(26),
		ToFTriggered:                  p.int(27),
		DiffIMUWheelYawSpeedTriggered: p.int(28),
		IMUNoRotationTriggered:        p.int(29),
		RotationTimeoutTriggered:      p.int(30),
	}
	return s, p.err("T")
}

// ParseObstacles parses an AT+S2 reply payload ("S2,count,r,g,b,n,x,y,...")
// into one polygon per obstacle. The display color is ignored.
func ParseObstacles(payload string) ([][]geo.Point, error) {
	f, err := fields(payload, "S2", 1)
	if err != nil {
		return nil, err
	}
	p := parser{fields: f}
	count := p.int(0)
	if err := p.err("S2"); err != nil {
		return nil, err
	}
	// Every obstacle needs at least its 4 header fields; this also bounds the allocation.
	if count < 0 || count > (len(f)-1)/4 {
		return nil, fmt.Errorf("%w: S2 announces %d obstacles in %d fields", ErrMalformed, count, len(f)-1)
	}
	obstacles := make([][]geo.Point, 0, count)
	i := 1
	for range count {
		// r, g, b, number of points
		if i+4 > len(f) {
			return nil, fmt.Errorf("%w: S2 ends inside obstacle header", ErrMalformed)
		}
		n := p.int(i + 3)
		i += 4
		if n < 0 || n > (len(f)-i)/2 {
			return nil, fmt.Errorf("%w: S2 obstacle with %d points does not fit the message", ErrMalformed, n)
		}
		poly := make([]geo.Point, n)
		for j := range poly {
			poly[j] = geo.Point{X: p.float(i), Y: p.float(i + 1)}
			i += 2
		}
		obstacles = append(obstacles, poly)
	}
	if err := p.err("S2"); err != nil {
		return nil, err
	}
	return obstacles, nil
}

// ParseWaypointAck parses the AT+W reply ("W,next") and returns the index
// of the next point the robot expects.
func ParseWaypointAck(payload string) (int, error) {
	f, err := fields(payload, "W", 1)
	if err != nil {
		return 0, err
	}
	p := parser{fields: f}
	next := p.int(0)
	return next, p.err("W")
}

// fields checks the reply name and returns the values after it.
func fields(payload, name string, minFields int) ([]string, error) {
	parts := strings.Split(payload, ",")
	if parts[0] != name {
		return nil, fmt.Errorf("%w: expected %s reply, got %q", ErrMalformed, name, parts[0])
	}
	if len(parts)-1 < minFields {
		return nil, fmt.Errorf("%w: %s reply has %d fields, want at least %d", ErrMalformed, name, len(parts)-1, minFields)
	}
	return parts[1:], nil
}

// parser reads fields by index and remembers the first error, so parse
// functions stay a flat list of assignments. Missing optional fields are zero.
type parser struct {
	fields []string
	first  error
}

func (p *parser) str(i int) string {
	if i >= len(p.fields) {
		return ""
	}
	return p.fields[i]
}

// float parses numbers leniently: the firmware prints C floats ("12.30",
// "nan") and integers without a fixed format.
func (p *parser) float(i int) float64 {
	if i >= len(p.fields) {
		return 0
	}
	return p.parse(i, p.fields[i])
}

// int reads an integer field. The firmware's integers are at most 32 bit;
// larger values are rejected so they cannot overflow index arithmetic.
func (p *parser) int(i int) int {
	v := p.float(i)
	if math.IsNaN(v) {
		return 0
	}
	if v < math.MinInt32 || v > math.MaxInt32 {
		if p.first == nil {
			p.first = fmt.Errorf("field %d %q: out of 32 bit range", i+1, p.fields[i])
		}
		return 0
	}
	return int(v)
}

// amps handles the charging current, which the firmware prefixes with "-".
// If the board already reports it negative, the result is "--x".
func (p *parser) amps(i int) float64 {
	if i < len(p.fields) {
		if rest, ok := strings.CutPrefix(p.fields[i], "--"); ok {
			return -p.parse(i, rest)
		}
	}
	return p.float(i)
}

func (p *parser) parse(i int, s string) float64 {
	v, err := strconv.ParseFloat(strings.TrimSpace(s), 64)
	if err != nil && p.first == nil {
		p.first = fmt.Errorf("field %d %q: %w", i+1, p.fields[i], err)
	}
	return v
}

func (p *parser) err(name string) error {
	if p.first != nil {
		return fmt.Errorf("%w: %s reply: %w", ErrMalformed, name, p.first)
	}
	return nil
}
