package protocol

import (
	"math"
	"strconv"
	"strings"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
)

// Requests without arguments.
const (
	RequestVersion   = "AT+V"
	RequestState     = "AT+S"
	RequestStats     = "AT+T"
	RequestObstacles = "AT+S2"
	Reboot           = "AT+Y"
	RebootGPS        = "AT+Y2"
	Shutdown         = "AT+Y3"
)

// Op is the robot operation (OperationType in the firmware).
type Op int

const (
	OpIdle Op = iota
	OpMow
	OpCharge
	OpError
	OpDock
)

func (o Op) String() string {
	switch o {
	case OpIdle:
		return "idle"
	case OpMow:
		return "mow"
	case OpCharge:
		return "charge"
	case OpError:
		return "error"
	case OpDock:
		return "dock"
	}
	return "op(" + strconv.Itoa(int(o)) + ")"
}

// Opt is an optional AT+C value. The zero value means "leave unchanged",
// so an empty Control never changes anything on the robot.
type Opt[T any] struct {
	Value T
	Set   bool
}

// Some returns an Opt that sets v.
func Some[T any](v T) Opt[T] {
	return Opt[T]{Value: v, Set: true}
}

// Control is the AT+C command. Fields are in wire order:
// AT+C,mow,op,spd,fixTO,restart,perc,skip,sonar,pwm,height,dock
type Control struct {
	MowMotor         Opt[bool]
	Op               Opt[Op]
	SpeedMps         Opt[float64]
	FixTimeoutSec    Opt[int]
	FinishAndRestart Opt[bool]
	// MowProgress jumps to a fraction (0..1) of the mow points.
	MowProgress   Opt[float64]
	SkipNextPoint bool
	Sonar         Opt[bool]
	MowPWM        Opt[int]
	MowHeightMM   Opt[int]
	// DockAfterFinish docks when all mow points are done.
	DockAfterFinish Opt[bool]
}

// Encode returns the AT+C payload.
func (c Control) Encode() string {
	skip := Opt[bool]{}
	if c.SkipNextPoint {
		skip = Some(true)
	}
	return "AT+C," + strings.Join([]string{
		optBool(c.MowMotor),
		optInt(Opt[int]{Value: int(c.Op.Value), Set: c.Op.Set}),
		optFloat(c.SpeedMps),
		optInt(c.FixTimeoutSec),
		optBool(c.FinishAndRestart),
		optFloat(c.MowProgress),
		optBool(skip),
		optBool(c.Sonar),
		optInt(c.MowPWM),
		optInt(c.MowHeightMM),
		optBool(c.DockAfterFinish),
	}, ",")
}

// Stop switches the robot to idle, which stops all motors immediately.
func Stop() Control {
	return Control{MowMotor: Some(false), Op: Some(OpIdle)}
}

// Dock drives the robot to the docking station.
func Dock() Control {
	return Control{MowMotor: Some(false), Op: Some(OpDock)}
}

// Mow starts mowing the uploaded mow points.
func Mow(speedMps float64, fixTimeoutSec int, finishAndRestart bool) Control {
	return Control{
		MowMotor:         Some(true),
		Op:               Some(OpMow),
		SpeedMps:         Some(speedMps),
		FixTimeoutSec:    Some(fixTimeoutSec),
		FinishAndRestart: Some(finishAndRestart),
		DockAfterFinish:  Some(true),
	}
}

// Goto drives along the uploaded way points with the mow motor off.
func Goto(speedMps float64, fixTimeoutSec int) Control {
	return Control{
		MowMotor:         Some(false),
		Op:               Some(OpMow),
		SpeedMps:         Some(speedMps),
		FixTimeoutSec:    Some(fixTimeoutSec),
		FinishAndRestart: Some(false),
		DockAfterFinish:  Some(false),
	}
}

// MowMotor switches the mow motor without changing the operation.
func MowMotor(on bool) Control {
	return Control{MowMotor: Some(on)}
}

// Speed changes the driving speed of the current operation.
func Speed(speedMps float64) Control {
	return Control{SpeedMps: Some(speedMps)}
}

// SkipNextPoint continues with the next mow point.
func SkipNextPoint() Control {
	return Control{SkipNextPoint: true}
}

// SkipToProgress continues at a fraction (0..1) of the mow points.
func SkipToProgress(fraction float64) Control {
	return Control{MowProgress: Some(fraction)}
}

// Move drives manually (joystick): linear in m/s, angular in rad/s.
// Move(0, 0) stops the motors.
func Move(linearMps, angularRadps float64) string {
	return "AT+M," + formatFloat(linearMps) + "," + formatFloat(angularRadps)
}

// PositionMode sets relative positioning, or absolute positioning around a
// reference point given as longitude/latitude.
func PositionMode(absolute bool, lon, lat float64) string {
	return "AT+P," + boolDigit(absolute) + "," + formatFloat(lon) + "," + formatFloat(lat)
}

// Map is everything the robot needs to navigate, in upload order.
type Map struct {
	Perimeter  []geo.Point
	Exclusions [][]geo.Point
	Dock       []geo.Point
	// Way is the route to drive: mow points for mowing, a path for goto.
	Way []geo.Point
}

// waypointsPerMessage keeps AT+W messages short enough for the robot's buffer.
const waypointsPerMessage = 30

// MapUpload returns the payloads that transfer m to the robot: AT+W messages
// with all points, then the counts per section (AT+N) and per exclusion (AT+X).
// Coordinates are sent in centimeter precision.
func MapUpload(m Map) []string {
	points := make([]geo.Point, 0, len(m.Perimeter)+len(m.Dock)+len(m.Way))
	points = append(points, m.Perimeter...)
	exclusionPoints := 0
	exclusionLengths := make([]string, len(m.Exclusions))
	for i, ex := range m.Exclusions {
		points = append(points, ex...)
		exclusionPoints += len(ex)
		exclusionLengths[i] = strconv.Itoa(len(ex))
	}
	points = append(points, m.Dock...)
	points = append(points, m.Way...)

	var msgs []string
	for start := 0; start < len(points); start += waypointsPerMessage {
		end := min(start+waypointsPerMessage, len(points))
		var b strings.Builder
		b.WriteString("AT+W,")
		b.WriteString(strconv.Itoa(start))
		for _, p := range points[start:end] {
			b.WriteString(",")
			b.WriteString(formatCoord(p.X))
			b.WriteString(",")
			b.WriteString(formatCoord(p.Y))
		}
		msgs = append(msgs, b.String())
	}

	// The last count are "free" points, which CaSSAndRA does not use.
	msgs = append(msgs, "AT+N,"+strings.Join([]string{
		strconv.Itoa(len(m.Perimeter)),
		strconv.Itoa(exclusionPoints),
		strconv.Itoa(len(m.Dock)),
		strconv.Itoa(len(m.Way)),
		"0",
	}, ","))
	msgs = append(msgs, strings.Join(append([]string{"AT+X", "0"}, exclusionLengths...), ","))
	return msgs
}

func optBool(o Opt[bool]) string {
	if !o.Set {
		return "-1"
	}
	return boolDigit(o.Value)
}

func optInt(o Opt[int]) string {
	if !o.Set {
		return "-1"
	}
	return strconv.Itoa(o.Value)
}

func optFloat(o Opt[float64]) string {
	if !o.Set {
		return "-1"
	}
	return formatFloat(o.Value)
}

func boolDigit(b bool) string {
	if b {
		return "1"
	}
	return "0"
}

func formatFloat(v float64) string {
	return strconv.FormatFloat(v, 'f', -1, 64)
}

func formatCoord(v float64) string {
	r := math.Round(v*100) / 100
	if r == 0 {
		r = 0 // avoid "-0"
	}
	return formatFloat(r)
}
