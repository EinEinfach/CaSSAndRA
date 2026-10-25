package robot_test

import (
	"context"
	"reflect"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
)

func TestStatusFromState(t *testing.T) {
	ctx := context.Background()
	tests := []struct {
		name  string
		setup func(f fixture)
		want  robot.Status
	}{
		{"never connected", func(fixture) {}, robot.StatusOffline},
		{"connected without state", func(f fixture) { f.robot.OnOnline(true) }, robot.StatusOffline},
		{"idle", func(f fixture) { f.online(state(protocol.OpIdle)) }, robot.StatusIdle},
		{"mowing", func(f fixture) {
			f.online(state(protocol.OpIdle))
			_ = f.robot.Mow(ctx)
			f.robot.OnState(state(protocol.OpMow))
		}, robot.StatusMow},
		{"mow op without mow motor is transit", func(f fixture) {
			f.online(state(protocol.OpIdle))
			_ = f.robot.Goto(ctx)
			f.robot.OnState(state(protocol.OpMow))
		}, robot.StatusTransit},
		{"docking", func(f fixture) { f.online(state(protocol.OpDock)) }, robot.StatusDocking},
		{"charging", func(f fixture) {
			s := state(protocol.OpCharge)
			s.Amps = -1.2
			f.online(s)
		}, robot.StatusCharging},
		{"charge op at threshold is still charging", func(f fixture) {
			s := state(protocol.OpCharge)
			s.Amps = -0.03
			f.online(s)
		}, robot.StatusCharging},
		{"docked with full battery", func(f fixture) {
			s := state(protocol.OpCharge)
			s.Amps = -0.01
			f.online(s)
		}, robot.StatusDocked},
		{"error", func(f fixture) { f.online(state(protocol.OpError)) }, robot.StatusError},
		{"unknown op", func(f fixture) { f.online(state(protocol.Op(9))) }, robot.StatusUnknown},
		{"manual move", func(f fixture) {
			f.online(state(protocol.OpIdle))
			_ = f.robot.Move(ctx, 0.2, 0)
		}, robot.StatusMove},
		{"manual move ends 2 s after the last command", func(f fixture) {
			f.online(state(protocol.OpIdle))
			_ = f.robot.Move(ctx, 0.2, 0)
			f.clock.Advance(2 * time.Second)
		}, robot.StatusIdle},
		{"move with zero speed ends at once", func(f fixture) {
			f.online(state(protocol.OpIdle))
			_ = f.robot.Move(ctx, 0.2, 0)
			_ = f.robot.Move(ctx, 0, 0)
		}, robot.StatusIdle},
		{"state older than 60 s", func(f fixture) {
			f.online(state(protocol.OpIdle))
			f.clock.Advance(61 * time.Second)
		}, robot.StatusOffline},
		{"state exactly 60 s old", func(f fixture) {
			f.online(state(protocol.OpIdle))
			f.clock.Advance(60 * time.Second)
		}, robot.StatusIdle},
		{"link went offline", func(f fixture) {
			f.online(state(protocol.OpMow))
			f.robot.OnOnline(false)
		}, robot.StatusOffline},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			tt.setup(f)
			if got := f.robot.Snapshot().Status; got != tt.want {
				t.Errorf("status = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestFirmwareSwitchesMowMotorOff(t *testing.T) {
	for _, op := range []protocol.Op{protocol.OpDock, protocol.OpCharge, protocol.OpError} {
		t.Run(op.String(), func(t *testing.T) {
			f := newFixture(t)
			f.online(state(protocol.OpIdle))
			_ = f.robot.Mow(context.Background())
			f.robot.OnState(state(protocol.OpMow))

			f.robot.OnState(state(op))
			f.robot.OnState(state(protocol.OpMow)) // e.g. resumed by the firmware itself

			if snap := f.robot.Snapshot(); snap.MowMotorOn || snap.Status != robot.StatusTransit {
				t.Errorf("mow motor on = %v, status %q; want off / transit", snap.MowMotorOn, snap.Status)
			}
		})
	}
}

func TestStateOfCharge(t *testing.T) {
	tests := []struct {
		voltage float64
		want    int
	}{
		{22, 0}, {21, 0}, {25, 50}, {25.03, 51}, {28, 100}, {29.5, 100},
	}
	for _, tt := range tests {
		f := newFixture(t)
		s := state(protocol.OpIdle)
		s.BatteryVoltage = tt.voltage
		f.online(s)
		if got := f.robot.Snapshot().SoCPercent; got != tt.want {
			t.Errorf("SoC at %.2f V = %d %%, want %d %%", tt.voltage, got, tt.want)
		}
	}
	if got := newFixture(t).robot.Snapshot().SoCPercent; got != 0 {
		t.Errorf("SoC without state = %d, want 0", got)
	}
}

func TestDockReason(t *testing.T) {
	docking := func(sensor protocol.Sensor, idx int) protocol.State {
		s := state(protocol.OpDock)
		s.Sensor, s.MowPointIndex = sensor, idx
		return s
	}
	tests := []struct {
		name  string
		setup func(f fixture)
		want  robot.DockReason
	}{
		{"not docking", func(f fixture) { f.online(state(protocol.OpMow)) }, robot.DockReasonNone},
		{"user pressed dock", func(f fixture) {
			f.online(state(protocol.OpMow))
			_ = f.robot.Dock(context.Background())
			f.robot.OnState(docking(0, 42))
		}, robot.DockReasonUser},
		{"sent home by the schedule", func(f fixture) {
			f.online(state(protocol.OpMow))
			_ = f.robot.DockFor(context.Background(), robot.DockReasonSchedule)
			f.robot.OnState(docking(0, 42))
		}, robot.DockReasonSchedule},
		{"rain", func(f fixture) { f.online(docking(16, 42)) }, robot.DockReasonRain},
		{"temperature", func(f fixture) { f.online(docking(18, 42)) }, robot.DockReasonTemperature},
		{"route finished", func(f fixture) { f.online(docking(0, 0)) }, robot.DockReasonFinished},
		{"low battery", func(f fixture) { f.online(docking(0, 42)) }, robot.DockReasonLowBattery},
		{"reason is decided once", func(f fixture) {
			f.online(docking(16, 42))
			f.robot.OnState(docking(0, 0))
		}, robot.DockReasonRain},
		{"kept while charging", func(f fixture) {
			f.online(docking(16, 42))
			f.robot.OnState(state(protocol.OpCharge))
		}, robot.DockReasonRain},
		{"cleared when leaving the dock", func(f fixture) {
			f.online(docking(16, 42))
			f.robot.OnState(state(protocol.OpCharge))
			f.robot.OnState(state(protocol.OpMow))
		}, robot.DockReasonNone},
		{"user flag only applies to the next docking", func(f fixture) {
			f.online(state(protocol.OpMow))
			_ = f.robot.Dock(context.Background())
			f.robot.OnState(docking(0, 42))
			f.robot.OnState(state(protocol.OpMow))
			f.robot.OnState(docking(0, 42))
		}, robot.DockReasonLowBattery},
		{"failed dock command is not the user's reason", func(f fixture) {
			f.online(state(protocol.OpMow))
			f.sender.fail["AT+C"] = 1
			_ = f.robot.Dock(context.Background())
			f.robot.OnState(docking(0, 42))
		}, robot.DockReasonLowBattery},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			tt.setup(f)
			if got := f.robot.Snapshot().DockReason; got != tt.want {
				t.Errorf("dock reason = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestSnapshotReportsEverything(t *testing.T) {
	f := newFixture(t)
	f.robot.OnVersion(protocol.Version{Firmware: "Sunray", Version: "1.0.332"})
	s := protocol.State{
		BatteryVoltage: 27.1, X: 1.5, Y: -2, HeadingRad: 0.7, Solution: protocol.SolutionFloat,
		Op: protocol.OpMow, MowPointIndex: 12, Sensor: 2, TargetX: 3, TargetY: 4, AccuracyM: 0.05,
		Satellites: 21, Amps: 0.6, MapCRC: 4711, LateralErrorM: 0.03,
		DGPSAgeSec: 1.5, SatellitesDGPS: 12,
	}
	f.online(s)
	f.robot.OnStats(protocol.Stats{DurationMowSec: 99})
	f.robot.OnObstacles([][]geo.Point{pts(1, 1, 2, 2, 3, 1)})

	got := f.robot.Snapshot()
	want := robot.Snapshot{
		Status: robot.StatusTransit, Online: true, Firmware: "Sunray", FirmwareVersion: "1.0.332",
		Position: geo.Point{X: 1.5, Y: -2}, HeadingRad: 0.7, Target: geo.Point{X: 3, Y: 4},
		BatteryV: 27.1, SoCPercent: 85, Amps: 0.6, Solution: protocol.SolutionFloat, AccuracyM: 0.05,
		Satellites: 21, Op: protocol.OpMow, Sensor: 2, MowPointIndex: 12, MapCRC: 4711, UpdatedAt: t0,
		TrailID: t0.UnixMilli(), LateralErrorM: 0.03, StatsAt: t0,
		DGPSAgeSec: 1.5, SatellitesDGPS: 12,
		Stats: protocol.Stats{DurationMowSec: 99}, Obstacles: [][]geo.Point{pts(1, 1, 2, 2, 3, 1)},
	}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("snapshot\n got %+v\nwant %+v", got, want)
	}
}
