package robot

import (
	"math"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// Status is what the robot is doing, as shown to the user.
type Status string

const (
	StatusOffline   Status = "offline"
	StatusIdle      Status = "idle"
	StatusMove      Status = "move" // manual driving
	StatusMapUpload Status = "map upload"
	StatusMow       Status = "mow"
	StatusTransit   Status = "transit" // driving with the mow motor off
	StatusDocking   Status = "docking"
	StatusCharging  Status = "charging"
	StatusDocked    Status = "docked"
	StatusError     Status = "error"
	StatusUnknown   Status = "unknown"
)

// DockReason explains why the robot is docking or docked.
type DockReason string

const (
	DockReasonNone        DockReason = ""
	DockReasonUser        DockReason = "user"
	DockReasonSchedule    DockReason = "schedule"
	DockReasonFinished    DockReason = "finished"
	DockReasonLowBattery  DockReason = "low battery"
	DockReasonRain        DockReason = "rain"
	DockReasonTemperature DockReason = "temperature"
)

// Sensor values that send the robot home (Sensor enum in the firmware).
const (
	sensorRain        protocol.Sensor = 16
	sensorTemperature protocol.Sensor = 18
)

// manualMoveHold keeps the status "move" after the last joystick command.
const manualMoveHold = 2 * time.Second

// Snapshot is a consistent copy of everything known about the robot.
type Snapshot struct {
	Status          Status
	Online          bool
	Firmware        string
	FirmwareVersion string
	Position        geo.Point
	HeadingRad      float64
	Target          geo.Point
	BatteryV        float64
	SoCPercent      int
	Amps            float64
	Solution        protocol.Solution
	AccuracyM       float64
	Satellites      int
	Op              protocol.Op
	Sensor          protocol.Sensor
	MowMotorOn      bool
	MowPointIndex   int
	DockReason      DockReason
	MapCRC          int64
	UpdatedAt       time.Time // last state report; zero if none yet
	LateralErrorM   float64   // distance from the line to the target
	StatsAt         time.Time // last AT+T report; zero if none yet
	TrailID         int64     // changes when the trail starts anew
	Stats           protocol.Stats
	Obstacles       [][]geo.Point
}

// Snapshot returns the current robot state.
func (r *Robot) Snapshot() Snapshot {
	r.mu.Lock()
	defer r.mu.Unlock()
	s := r.state
	obstacles := make([][]geo.Point, len(r.obstacles))
	copy(obstacles, r.obstacles)
	return Snapshot{
		Status:          r.statusLocked(),
		Online:          r.online,
		Firmware:        r.version.Firmware,
		FirmwareVersion: r.version.Version,
		Position:        geo.Point{X: s.X, Y: s.Y},
		HeadingRad:      s.HeadingRad,
		Target:          geo.Point{X: s.TargetX, Y: s.TargetY},
		BatteryV:        s.BatteryVoltage,
		SoCPercent:      r.socLocked(),
		Amps:            s.Amps,
		Solution:        s.Solution,
		AccuracyM:       s.AccuracyM,
		Satellites:      s.Satellites,
		Op:              s.Op,
		Sensor:          s.Sensor,
		MowMotorOn:      r.mowMotor,
		MowPointIndex:   s.MowPointIndex,
		DockReason:      r.dockReason,
		MapCRC:          s.MapCRC,
		UpdatedAt:       r.stateAt,
		LateralErrorM:   s.LateralErrorM,
		StatsAt:         r.statsAt,
		TrailID:         r.trail.id,
		Stats:           r.stats,
		Obstacles:       obstacles,
	}
}

func (r *Robot) statusLocked() Status {
	now := r.cfg.Now()
	if !r.online || r.stateAt.IsZero() || now.Sub(r.stateAt) > r.cfg.OfflineAfter {
		return StatusOffline
	}
	if r.uploading {
		return StatusMapUpload
	}
	switch r.state.Op {
	case protocol.OpIdle:
		if now.Before(r.moveUntil) {
			return StatusMove
		}
		return StatusIdle
	case protocol.OpMow:
		if r.mowMotor {
			return StatusMow
		}
		return StatusTransit
	case protocol.OpCharge:
		if r.state.Amps <= r.cfg.ChargingBelowA {
			return StatusCharging
		}
		return StatusDocked
	case protocol.OpError:
		return StatusError
	case protocol.OpDock:
		return StatusDocking
	}
	return StatusUnknown
}

func (r *Robot) socLocked() int {
	span := r.cfg.BatteryFullV - r.cfg.BatteryEmptyV
	if span <= 0 || r.stateAt.IsZero() {
		return 0
	}
	soc := (r.state.BatteryVoltage - r.cfg.BatteryEmptyV) / span * 100
	return int(math.Round(math.Max(0, math.Min(100, soc))))
}

// updateDockReasonLocked follows the legacy rules: the reason is decided
// once when docking starts and kept until the robot leaves the dock.
func (r *Robot) updateDockReasonLocked(s protocol.State) {
	switch s.Op {
	case protocol.OpDock:
		if r.dockReason != DockReasonNone {
			return
		}
		switch {
		case r.dockAsked != DockReasonNone:
			r.dockReason = r.dockAsked
		case s.Sensor == sensorTemperature:
			r.dockReason = DockReasonTemperature
		case s.Sensor == sensorRain:
			r.dockReason = DockReasonRain
		case s.MowPointIndex == 0: // the firmware resets the index after the last point
			r.dockReason = DockReasonFinished
		default:
			r.dockReason = DockReasonLowBattery
		}
		r.dockAsked = DockReasonNone
	case protocol.OpCharge:
		// keep the reason while docked
	default:
		r.dockReason = DockReasonNone
	}
}
