package link_test

import (
	"context"
	"errors"
	"math"
	"strings"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

func TestSimAnswersAllPollRequests(t *testing.T) {
	s := newSim(t)

	v, err := protocol.ParseVersion(send(t, s, protocol.RequestVersion))
	if err != nil || v.Firmware != "Sunray" || v.Encrypted {
		t.Errorf("version = %+v, %v; want unencrypted Sunray", v, err)
	}
	st, err := protocol.ParseState(send(t, s, protocol.RequestState))
	if err != nil || st.Op != protocol.OpIdle || st.X != 0 || st.Y != -2 || st.BatteryVoltage != 28.5 {
		t.Errorf("state = %+v, %v; want idle at (0,-2) with full battery", st, err)
	}
	if _, err := protocol.ParseStats(send(t, s, protocol.RequestStats)); err != nil {
		t.Errorf("stats: %v", err)
	}
	if o, err := protocol.ParseObstacles(send(t, s, protocol.RequestObstacles)); err != nil || len(o) != 0 {
		t.Errorf("obstacles = %v, %v; want none", o, err)
	}
}

func TestSimIgnoresInvalidRequests(t *testing.T) {
	s := newSim(t)
	for _, line := range []string{
		"AT+S,0x00\n",                 // wrong checksum
		protocol.Frame("AT+Q") + "\n", // unknown command
		protocol.Frame("S") + "\n",    // not a request
		"AT+S\n",                      // no checksum
	} {
		if _, err := s.Exchange(context.Background(), line); !errors.Is(err, link.ErrNoReply) {
			t.Errorf("Exchange(%q) err = %v, want ErrNoReply", line, err)
		}
	}
}

func TestSimOfflineAndCancelledContext(t *testing.T) {
	s := newSim(t)
	s.SetOffline(true)
	if _, err := s.Exchange(context.Background(), protocol.Frame("AT+S")); !errors.Is(err, link.ErrSimOffline) {
		t.Errorf("offline err = %v, want ErrSimOffline", err)
	}
	s.SetOffline(false)
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := s.Exchange(ctx, protocol.Frame("AT+S")); !errors.Is(err, context.Canceled) {
		t.Errorf("cancelled err = %v, want context.Canceled", err)
	}
}

func TestSimEncryption(t *testing.T) {
	cfg := link.DefaultSimConfig()
	cfg.Password = 1234
	s := link.NewSim(cfg)

	v, err := protocol.ParseVersion(send(t, s, protocol.RequestVersion))
	if err != nil || !v.Encrypted || v.Challenge != 199 {
		t.Fatalf("version = %+v, %v; want encrypted with challenge 199", v, err)
	}
	key, err := protocol.Key(1234, v.Challenge)
	if err != nil {
		t.Fatal(err)
	}

	enc := protocol.Encrypt(protocol.Frame("AT+S"), key)
	line, err := s.Exchange(context.Background(), enc)
	if err != nil {
		t.Fatalf("encrypted request: %v", err)
	}
	if reply, err := protocol.Unframe(line); err != nil || !strings.HasPrefix(reply, "S,") {
		t.Errorf("reply = %q, %v; want unencrypted state", reply, err)
	}
	if _, err := s.Exchange(context.Background(), protocol.Frame("AT+S")); !errors.Is(err, link.ErrNoReply) {
		t.Errorf("plain request to encrypting robot err = %v, want ErrNoReply", err)
	}
}

func TestSimMapUpload(t *testing.T) {
	s := newSim(t)
	msgs := protocol.MapUpload(garden)
	replies := make([]string, len(msgs))
	for i, m := range msgs {
		replies[i] = send(t, s, m)
	}
	// 4 perimeter + 3 exclusion + 2 dock + 4 way points
	want := []string{"W,13", "N", "X,1"}
	for i := range want {
		if replies[i] != want[i] {
			t.Errorf("reply %d = %q, want %q", i, replies[i], want[i])
		}
	}
	// Sum of all coordinates in cm, as Map::calcMapCRC computes it.
	var crc int64
	for _, p := range append(append(append(append([]geo.Point{}, garden.Perimeter...), garden.Exclusions[0]...), garden.Dock...), garden.Way...) {
		crc += int64(p.X*100 + p.Y*100)
	}
	if got := s.State().MapCRC; got != crc {
		t.Errorf("MapCRC = %d, want %d", got, crc)
	}
}

func TestSimMowsRouteThenDocksAndCharges(t *testing.T) {
	s := newSim(t)
	upload(t, s, garden)
	send(t, s, protocol.Mow(0.5, 60, false).Encode())

	st := s.State()
	if st.Op != protocol.OpMow || st.Amps <= 0 {
		t.Fatalf("after mow command: %+v, want mowing", st)
	}

	st = stepUntil(t, s, time.Minute, func(st protocol.State) bool { return st.MowPointIndex >= 2 })
	// Point (9,1) is passed; the rest of the step already heads to (9,9).
	if math.Abs(st.X-9) > 1e-9 || st.Y < 1 || st.Y > 1.1 {
		t.Errorf("at mow point 2 robot is at (%.2f,%.2f), want just past (9,1) towards (9,9)", st.X, st.Y)
	}

	st = stepUntil(t, s, 5*time.Minute, func(st protocol.State) bool { return st.Op != protocol.OpMow })
	if st.Op != protocol.OpDock || st.MowPointIndex != 0 {
		t.Errorf("after the route: op %v, index %d; want dock with index reset to 0", st.Op, st.MowPointIndex)
	}

	st = stepUntil(t, s, 5*time.Minute, func(st protocol.State) bool { return st.Op == protocol.OpCharge })
	if st.X != 0 || st.Y != -2 {
		t.Errorf("charging at (%.2f,%.2f), want station (0,-2)", st.X, st.Y)
	}
	if st.Amps >= 0 {
		t.Errorf("amps while charging = %v, want negative", st.Amps)
	}
}

func TestSimGotoDoesNotDock(t *testing.T) {
	s := newSim(t)
	m := garden
	m.Way = pts(2, 2)
	upload(t, s, m)
	send(t, s, protocol.Goto(1, 60).Encode())

	st := stepUntil(t, s, time.Minute, func(st protocol.State) bool { return st.Op != protocol.OpMow })
	if st.Op != protocol.OpIdle || st.X != 2 || st.Y != 2 {
		t.Errorf("after goto: op %v at (%.2f,%.2f), want idle at (2,2)", st.Op, st.X, st.Y)
	}
}

func TestSimStopKeepsPosition(t *testing.T) {
	s := newSim(t)
	upload(t, s, garden)
	send(t, s, protocol.Mow(0.5, 60, false).Encode())
	s.Step(3 * time.Second)

	send(t, s, protocol.Stop().Encode())
	before := s.State()
	s.Step(10 * time.Second)
	after := s.State()

	if after.Op != protocol.OpIdle || after.X != before.X || after.Y != before.Y {
		t.Errorf("after stop: op %v moved from (%.2f,%.2f) to (%.2f,%.2f)", after.Op, before.X, before.Y, after.X, after.Y)
	}
}

func TestSimErrorsWithoutRoute(t *testing.T) {
	tests := []struct {
		name string
		cmd  string
	}{
		{"mow", protocol.Mow(0.3, 60, false).Encode()},
		{"dock", protocol.Dock().Encode()},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := newSim(t)
			send(t, s, tt.cmd)
			if st := s.State(); st.Op != protocol.OpError || st.Sensor.String() != "no map route" {
				t.Errorf("op %v sensor %v, want error / no map route", st.Op, st.Sensor)
			}
		})
	}
}

func TestSimDocksOnLowBatteryAndRain(t *testing.T) {
	t.Run("low battery", func(t *testing.T) {
		s := newSim(t)
		upload(t, s, garden)
		send(t, s, protocol.Mow(0.3, 60, false).Encode())
		s.SetBatteryVoltage(23.001)
		st := stepUntil(t, s, 10*time.Second, func(st protocol.State) bool { return st.Op != protocol.OpMow })
		if st.Op != protocol.OpDock {
			t.Errorf("op = %v, want dock", st.Op)
		}
	})
	t.Run("rain", func(t *testing.T) {
		s := newSim(t)
		upload(t, s, garden)
		send(t, s, protocol.Mow(0.3, 60, false).Encode())
		s.TriggerRain()
		if st := s.State(); st.Op != protocol.OpDock || st.Sensor.String() != "rain" {
			t.Errorf("op %v sensor %v, want dock / rain", st.Op, st.Sensor)
		}
	})
}

func TestSimChargesToFull(t *testing.T) {
	s := newSim(t)
	upload(t, s, garden)
	s.SetBatteryVoltage(25)
	send(t, s, protocol.Dock().Encode())
	stepUntil(t, s, 5*time.Minute, func(st protocol.State) bool { return st.Op == protocol.OpCharge })

	stepUntil(t, s, 30*time.Minute, func(st protocol.State) bool { return st.BatteryVoltage >= 28.5 })
	s.Step(time.Minute)
	if st := s.State(); st.BatteryVoltage != 28.5 || st.Amps < -0.03 {
		t.Errorf("full battery: %.2f V, %.2f A; want 28.5 V and charging current above -0.03 A", st.BatteryVoltage, st.Amps)
	}
}

func TestSimManualMoveExpires(t *testing.T) {
	s := newSim(t)
	send(t, s, protocol.Move(0.5, 0))
	s.Step(time.Second)
	if st := s.State(); math.Abs(st.X-0.5) > 1e-9 || st.Y != -2 {
		t.Errorf("after 1 s at 0.5 m/s: (%.3f,%.3f), want (0.5,-2)", st.X, st.Y)
	}
	s.Step(10 * time.Second)
	if st := s.State(); math.Abs(st.X-1.0) > 1e-9 {
		t.Errorf("manual move did not expire after 2 s: x = %.3f, want 1.0", st.X)
	}
}

// Like ChargeOp::onChargerDisconnected: driving off the contacts ends charging.
func TestSimDrivesOffTheDock(t *testing.T) {
	s := newSim(t)
	upload(t, s, garden)
	send(t, s, protocol.Dock().Encode())
	st := stepUntil(t, s, 5*time.Minute, func(st protocol.State) bool { return st.Op == protocol.OpCharge })

	send(t, s, protocol.Move(0, 0))
	s.Step(time.Second)
	if got := s.State(); got.Op != protocol.OpCharge || got.X != st.X || got.Y != st.Y {
		t.Fatalf("a zero move left the dock: %+v", got)
	}

	send(t, s, protocol.Move(-0.2, 0))
	s.Step(time.Second)
	got := s.State()
	if got.Op != protocol.OpIdle || math.Hypot(got.X-st.X, got.Y-st.Y) < 0.1 {
		t.Errorf("after driving back: op %v at (%.2f,%.2f), want idle away from (%.2f,%.2f)", got.Op, got.X, got.Y, st.X, st.Y)
	}
}

func TestSimSkipAndProgress(t *testing.T) {
	s := newSim(t)
	upload(t, s, garden)
	send(t, s, protocol.SkipNextPoint().Encode())
	if got := s.State().MowPointIndex; got != 1 {
		t.Errorf("after skip: index %d, want 1", got)
	}
	send(t, s, protocol.SkipToProgress(0.5).Encode())
	if got := s.State().MowPointIndex; got != 2 {
		t.Errorf("after progress 0.5 of 4 points: index %d, want 2", got)
	}
	send(t, s, protocol.SkipToProgress(1).Encode())
	if got := s.State().MowPointIndex; got != 3 {
		t.Errorf("after progress 1: index %d, want last point 3", got)
	}
}

func TestSimRepliesToSystemCommands(t *testing.T) {
	s := newSim(t)
	for _, tt := range []struct{ cmd, want string }{
		{protocol.PositionMode(true, 13.4, 52.5), "P"},
		{protocol.Reboot, "Y"},
		{protocol.RebootGPS, "Y2"},
		{protocol.Shutdown, "Y3"},
	} {
		if got := send(t, s, tt.cmd); got != tt.want {
			t.Errorf("%s -> %q, want %q", tt.cmd, got, tt.want)
		}
	}
	if _, err := s.Exchange(context.Background(), protocol.Frame("AT+S")); !errors.Is(err, link.ErrSimOffline) {
		t.Errorf("after shutdown err = %v, want ErrSimOffline", err)
	}
}

func TestSimStats(t *testing.T) {
	s := newSim(t)
	s.Step(10 * time.Second)
	upload(t, s, garden)
	send(t, s, protocol.Mow(0.5, 60, false).Encode())
	s.Step(4 * time.Second)

	st, err := protocol.ParseStats(send(t, s, protocol.RequestStats))
	if err != nil {
		t.Fatal(err)
	}
	if st.DurationIdleSec != 10 || st.DurationMowSec != 4 || math.Abs(st.DistanceMowTraveledM-2) > 0.01 {
		t.Errorf("stats = idle %d s, mow %d s, %.2f m; want 10 s, 4 s, 2 m", st.DurationIdleSec, st.DurationMowSec, st.DistanceMowTraveledM)
	}
}

func TestSimRunStepsInRealTime(t *testing.T) {
	s := newSim(t)
	send(t, s, protocol.Move(1, 0))
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()
	s.Run(ctx, 10*time.Millisecond)
	if x := s.State().X; x < 0.05 {
		t.Errorf("x = %.3f after 200 ms at 1 m/s, want the robot to have moved", x)
	}
}
