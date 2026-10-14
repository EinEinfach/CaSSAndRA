// Package integration_test runs features together against the simulator.
package integration_test

import (
	"context"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func pts(coords ...float64) []geo.Point {
	p := make([]geo.Point, len(coords)/2)
	for i := range p {
		p[i] = geo.Point{X: coords[2*i], Y: coords[2*i+1]}
	}
	return p
}

var garden = protocol.Map{
	Perimeter: pts(0, 0, 10, 0, 10, 10, 0, 10),
	Dock:      pts(0, 1, 0, -2),
	Way:       pts(1, 1, 9, 1, 9, 9, 1, 9),
}

type setup struct {
	sim   *link.Sim
	robot *robot.Robot
	stop  func()
}

// start wires robot -> poller -> simulator like the app does, with fast polling.
func start(t *testing.T, password int) setup {
	t.Helper()
	simCfg := link.DefaultSimConfig()
	simCfg.Start = geo.Point{X: 0, Y: -2}
	simCfg.Password = password
	sim := link.NewSim(simCfg)

	pollCfg := link.PollConfig{
		StateInterval:     5 * time.Millisecond,
		ObstaclesInterval: 20 * time.Millisecond,
		StatsInterval:     20 * time.Millisecond,
		ReconnectDelay:    10 * time.Millisecond,
		Encrypt:           password > 0,
		Password:          password,
	}
	poller := link.NewPoller(sim, pollCfg)

	robotCfg := robot.DefaultConfig()
	robotCfg.MowSpeedMps = 0.5
	robotCfg.Logger = testkit.Logger(t)
	r := robot.New(poller, robotCfg)

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- poller.Run(ctx, r) }()
	stop := func() {
		cancel()
		if err := <-done; err != nil {
			t.Errorf("poller: %v", err)
		}
	}
	t.Cleanup(func() {
		if ctx.Err() == nil {
			stop()
		}
	})
	return setup{sim: sim, robot: r, stop: stop}
}

// waitFor polls the robot snapshot until cond holds, while sim time advances
// by step per poll.
func (s setup) waitFor(t *testing.T, what string, step time.Duration, cond func(robot.Snapshot) bool) robot.Snapshot {
	t.Helper()
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		if snap := s.robot.Snapshot(); cond(snap) {
			return snap
		}
		s.sim.Step(step)
		time.Sleep(2 * time.Millisecond)
	}
	snap := s.robot.Snapshot()
	t.Fatalf("timed out waiting for %s; last snapshot: status %q at %v, op %v", what, snap.Status, snap.Position, snap.Op)
	return snap
}

func TestMowStopDock(t *testing.T) {
	for _, tc := range []struct {
		name     string
		password int
	}{
		{"plain link", 0},
		{"encrypted link", 1234},
	} {
		t.Run(tc.name, func(t *testing.T) {
			s := start(t, tc.password)
			ctx := context.Background()

			snap := s.waitFor(t, "robot online and idle", 0, func(r robot.Snapshot) bool { return r.Status == robot.StatusIdle })
			if snap.Firmware != "Sunray" || snap.Position != (geo.Point{X: 0, Y: -2}) || snap.SoCPercent != 100 {
				t.Errorf("initial snapshot = %+v", snap)
			}

			if err := s.robot.UploadMap(ctx, garden); err != nil {
				t.Fatalf("upload: %v", err)
			}
			if err := s.robot.Mow(ctx); err != nil {
				t.Fatalf("mow: %v", err)
			}
			snap = s.waitFor(t, "mowing past the first point", 200*time.Millisecond, func(r robot.Snapshot) bool {
				return r.Status == robot.StatusMow && r.MowPointIndex >= 1
			})
			if !snap.MowMotorOn {
				t.Error("mow motor off while mowing")
			}

			if err := s.robot.Stop(ctx); err != nil {
				t.Fatalf("stop: %v", err)
			}
			s.waitFor(t, "idle after stop", 0, func(r robot.Snapshot) bool { return r.Status == robot.StatusIdle })
			before := s.sim.State()
			s.sim.Step(10 * time.Second)
			if after := s.sim.State(); after.X != before.X || after.Y != before.Y {
				t.Errorf("robot moved after stop: (%v,%v) -> (%v,%v)", before.X, before.Y, after.X, after.Y)
			}

			if err := s.robot.Dock(ctx); err != nil {
				t.Fatalf("dock: %v", err)
			}
			s.waitFor(t, "docking", 0, func(r robot.Snapshot) bool { return r.Status == robot.StatusDocking })
			snap = s.waitFor(t, "charging at the station", time.Second, func(r robot.Snapshot) bool {
				return r.Status == robot.StatusCharging || r.Status == robot.StatusDocked
			})
			if snap.Position != (geo.Point{X: 0, Y: -2}) || snap.DockReason != robot.DockReasonUser {
				t.Errorf("docked at %v because %q, want station because user", snap.Position, snap.DockReason)
			}

			s.stop()
			if st := s.robot.Snapshot().Status; st != robot.StatusOffline {
				t.Errorf("status after link stopped = %q, want offline", st)
			}
		})
	}
}

func TestFinishedRouteDocksWithReasonFinished(t *testing.T) {
	s := start(t, 0)
	ctx := context.Background()
	s.waitFor(t, "online", 0, func(r robot.Snapshot) bool { return r.Online && r.Status == robot.StatusIdle })

	if err := s.robot.UploadMap(ctx, garden); err != nil {
		t.Fatal(err)
	}
	if err := s.robot.Mow(ctx); err != nil {
		t.Fatal(err)
	}
	snap := s.waitFor(t, "docking after the route", 2*time.Second, func(r robot.Snapshot) bool {
		return r.Status == robot.StatusDocking
	})
	if snap.DockReason != robot.DockReasonFinished || snap.MowMotorOn {
		t.Errorf("dock reason %q, mow motor %v; want finished, off", snap.DockReason, snap.MowMotorOn)
	}
}

func TestRainSendsTheRobotHome(t *testing.T) {
	s := start(t, 0)
	ctx := context.Background()
	s.waitFor(t, "online", 0, func(r robot.Snapshot) bool { return r.Status == robot.StatusIdle })
	if err := s.robot.UploadMap(ctx, garden); err != nil {
		t.Fatal(err)
	}
	if err := s.robot.Mow(ctx); err != nil {
		t.Fatal(err)
	}
	s.waitFor(t, "mowing", 500*time.Millisecond, func(r robot.Snapshot) bool { return r.MowPointIndex >= 1 })

	s.sim.TriggerRain()
	snap := s.waitFor(t, "docking", 0, func(r robot.Snapshot) bool { return r.Status == robot.StatusDocking })
	if snap.DockReason != robot.DockReasonRain {
		t.Errorf("dock reason = %q, want rain", snap.DockReason)
	}
}

func TestConnectionLossAndRecovery(t *testing.T) {
	s := start(t, 0)
	s.waitFor(t, "online", 0, func(r robot.Snapshot) bool { return r.Status == robot.StatusIdle })

	s.sim.SetOffline(true)
	s.waitFor(t, "offline", 0, func(r robot.Snapshot) bool { return r.Status == robot.StatusOffline })
	if err := s.robot.Dock(context.Background()); err == nil {
		t.Error("dock while offline succeeded, want error")
	}

	s.sim.SetOffline(false)
	s.waitFor(t, "online again", 0, func(r robot.Snapshot) bool { return r.Status == robot.StatusIdle })
}
