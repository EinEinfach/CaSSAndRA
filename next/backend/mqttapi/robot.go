package mqttapi

import (
	"context"
	"fmt"
	"math"
	"strconv"
	"strings"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
)

// RobotJSON is the payload of <prefix>/robot (legacy robottopic.py).
type RobotJSON struct {
	Firmware       string      `json:"firmware"`
	Version        string      `json:"version"`
	Status         string      `json:"status"`
	DockReason     *string     `json:"dockReason"`
	SensorState    string      `json:"sensorState"`
	Battery        batteryJSON `json:"battery"`
	Position       xyJSON      `json:"position"`
	Target         xyJSON      `json:"target"`
	Angle          Float       `json:"angle"`
	MowPointIdx    int         `json:"mowPointIdx"`
	GPS            gpsJSON     `json:"gps"`
	SecondsPerIdx  *Float      `json:"secondsPerIdx"`
	Speed          Float       `json:"speed"`
	AverageSpeed   Float       `json:"averageSpeed"`
	MowMotorActive bool        `json:"mowMotorActive"`
}

type batteryJSON struct {
	SoC             int   `json:"soc"`
	Voltage         Float `json:"voltage"`
	ElectricCurrent Float `json:"electricCurrent"`
}

type xyJSON struct {
	X Float `json:"x"`
	Y Float `json:"y"`
}

type gpsJSON struct {
	Visible  int    `json:"visible"`
	DGPS     int    `json:"dgps"`
	Age      string `json:"age"`
	Solution string `json:"solution"`
}

// legacySensors are the sensor texts of legacy CaSSAndRA (roverdata.py
// calc_sensor_status), which differ from the firmware's names.
var legacySensors = map[protocol.Sensor]string{
	0: "no error", 1: "undervoltage", 2: "obstacle", 3: "gps timeout", 4: "imu timeout",
	5: "imu tilt", 6: "kidnapped", 7: "overload", 8: "motor error", 9: "gps invalid",
	10: "odo error", 11: "no route", 12: "memory error", 13: "bumper error", 14: "sonar error",
	15: "lifted", 16: "rain sensor", 17: "emergency/stop", 18: "temperature out of range",
}

// legacyDockReasons maps our reasons to the legacy texts.
var legacyDockReasons = map[robot.DockReason]string{
	robot.DockReasonUser:        "operator",
	robot.DockReasonSchedule:    "schedule",
	robot.DockReasonFinished:    "finished",
	robot.DockReasonLowBattery:  "low battery",
	robot.DockReasonRain:        "rain",
	robot.DockReasonTemperature: "temperature",
}

// motion derives speed and seconds per route point from consecutive
// snapshots, like legacy roverdata.py (calc_speed, calc_seconds_per_idx).
type motion struct {
	last          robot.Snapshot
	speed         float64
	averageSpeed  float64
	secondsPerIdx *float64
	idxSince      time.Time // when lastIdx was seen first
	lastIdx       int
	dots          int // the legacy "..." animation in sensorState
}

func (m *motion) update(s robot.Snapshot) {
	if s.UpdatedAt.Equal(m.last.UpdatedAt) {
		return
	}
	defer func() { m.last = s }()
	m.dots = m.dots%5 + 1

	dt := s.UpdatedAt.Sub(m.last.UpdatedAt).Seconds()
	moving := s.Op == protocol.OpMow || s.Op == protocol.OpDock
	m.speed = 0
	if moving && !m.last.UpdatedAt.IsZero() && dt > 0 {
		m.speed = math.Round(math.Hypot(s.Position.X-m.last.Position.X, s.Position.Y-m.last.Position.Y)/dt*100) / 100
		m.averageSpeed = 0.999*m.averageSpeed + 0.001*m.speed
	}

	if s.Status != robot.StatusMow {
		m.idxSince = time.Time{}
		return
	}
	if m.idxSince.IsZero() {
		m.idxSince, m.lastIdx = s.UpdatedAt, s.MowPointIndex
		return
	}
	if d := s.MowPointIndex - m.lastIdx; d > 0 {
		cur := s.UpdatedAt.Sub(m.idxSince).Seconds() / float64(d)
		if cur < 300 {
			if m.secondsPerIdx == nil {
				m.secondsPerIdx = &cur
			} else {
				v := 0.999**m.secondsPerIdx + 0.001*cur
				m.secondsPerIdx = &v
			}
		}
		m.idxSince, m.lastIdx = s.UpdatedAt, s.MowPointIndex
	}
}

func (m *motion) payload(s robot.Snapshot) RobotJSON {
	var dock *string
	if r, ok := legacyDockReasons[s.DockReason]; ok {
		dock = &r
	}
	sensor := strings.Repeat(".", m.dots)
	switch {
	case s.Op == protocol.OpError:
		sensor = legacySensors[s.Sensor]
		if sensor == "" {
			sensor = "unknown"
		}
	case dock != nil:
		sensor = *dock
	}
	var spi *Float
	if m.secondsPerIdx != nil {
		spi = floatPtr(*m.secondsPerIdx)
	}
	return RobotJSON{
		Firmware:    s.Firmware,
		Version:     s.FirmwareVersion,
		Status:      string(s.Status),
		DockReason:  dock,
		SensorState: sensor,
		Battery: batteryJSON{
			SoC: s.SoCPercent, Voltage: round2(s.BatteryV), ElectricCurrent: round2(s.Amps),
		},
		Position:       xyJSON{round2(s.Position.X), round2(s.Position.Y)},
		Target:         xyJSON{round2(s.Target.X), round2(s.Target.Y)},
		Angle:          Float(s.HeadingRad),
		MowPointIdx:    s.MowPointIndex,
		GPS:            gpsJSON{Visible: s.Satellites, DGPS: s.SatellitesDGPS, Age: ageText(s), Solution: solutionText(s.Solution)},
		SecondsPerIdx:  spi,
		Speed:          Float(m.speed),
		AverageSpeed:   Float(m.averageSpeed),
		MowMotorActive: s.MowMotorOn,
	}
}

func solutionText(s protocol.Solution) string {
	switch s {
	case protocol.SolutionFix:
		return "fix"
	case protocol.SolutionFloat:
		return "float"
	default:
		return "invalid"
	}
}

// ageText is the age of the correction data as legacy calc_position_age_hr
// writes it ("0.53s", "12min", "3h", "99+d").
func ageText(s robot.Snapshot) string {
	age := s.DGPSAgeSec
	if s.UpdatedAt.IsZero() {
		return "99+d"
	}
	switch {
	case age >= 356400:
		return "99+d"
	case age >= 86400:
		return strconv.Itoa(int(age/86400)) + "d"
	case age >= 3600:
		return strconv.Itoa(int(age/3600)) + "h"
	case age >= 60:
		return strconv.Itoa(int(age/60)) + "min"
	}
	b, _ := round2(age).MarshalJSON()
	return string(b) + "s"
}

// Robot is what the API needs from the robot.
type Robot interface {
	Snapshot() robot.Snapshot
	Stop(ctx context.Context) error
	Dock(ctx context.Context) error
	Mow(ctx context.Context) error
	Move(ctx context.Context, linearMps, angularRadps float64) error
	SetSpeed(ctx context.Context, mps float64) error
	SetMowMotor(ctx context.Context, on bool) error
	SkipNextPoint(ctx context.Context) error
	SkipToProgress(ctx context.Context, fraction float64) error
	Reboot(ctx context.Context) error
	RebootGPS(ctx context.Context) error
	Shutdown(ctx context.Context) error
	// Map is the map last sent to the robot, with the route it follows.
	Map() protocol.Map
	ClearObstacles()
}

// robotCommand runs a command of the robot topic. Movement commands are
// sent once, like every other command (never repeated here).
func (a *API) robotCommand(ctx context.Context, c command) error {
	switch c.Command {
	case "stop":
		return a.robot.Stop(ctx)
	case "dock":
		return a.robot.Dock(ctx)
	case "move":
		v, err := c.numbers(2)
		if err != nil {
			return err
		}
		return a.robot.Move(ctx, v[0], v[1])
	case "mow":
		return a.mow(ctx, c)
	case "goTo":
		p, err := c.point()
		if err != nil {
			return err
		}
		_, err = a.tasks.Goto(ctx, p)
		return err
	case "reboot":
		return a.robot.Reboot(ctx)
	case "rebootGps":
		return a.robot.RebootGPS(ctx)
	case "shutdown":
		return a.robot.Shutdown(ctx)
	case "setMowSpeed", "setGoToSpeed":
		v, err := c.numbers(1)
		if err != nil {
			return err
		}
		return a.robot.SetSpeed(ctx, v[0])
	case "setMowProgress":
		v, err := c.numbers(1)
		if err != nil {
			return err
		}
		return a.robot.SkipToProgress(ctx, v[0])
	case "toggleMowMotor":
		return a.robot.SetMowMotor(ctx, !a.robot.Snapshot().MowMotorOn)
	case "skipNextPoint":
		// Legacy stopped, skipped and resumed after 3 s; the firmware skips
		// while driving, so the robot never gets an automatic second start.
		return a.robot.SkipNextPoint(ctx)
	}
	return fmt.Errorf("%w: robot command %q", ErrUnknown, c.Command)
}
