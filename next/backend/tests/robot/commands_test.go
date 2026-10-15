package robot_test

import (
	"context"
	"errors"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func TestCommandsSendTheirPayload(t *testing.T) {
	ctx := context.Background()
	tests := []struct {
		name string
		run  func(r *robot.Robot) error
		want string
	}{
		{"stop", func(r *robot.Robot) error { return r.Stop(ctx) }, "AT+C,0,0,-1,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"dock", func(r *robot.Robot) error { return r.Dock(ctx) }, "AT+C,0,4,-1,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"mow uses mow speed", func(r *robot.Robot) error { return r.Mow(ctx) }, "AT+C,1,1,0.25,60,0,-1,-1,-1,-1,-1,1"},
		{"goto uses goto speed", func(r *robot.Robot) error { return r.Goto(ctx) }, "AT+C,0,1,0.3,60,0,-1,-1,-1,-1,-1,0"},
		{"move", func(r *robot.Robot) error { return r.Move(ctx, 0.2, -0.4) }, "AT+M,0.2,-0.4"},
		{"mow motor", func(r *robot.Robot) error { return r.SetMowMotor(ctx, true) }, "AT+C,1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"speed", func(r *robot.Robot) error { return r.SetSpeed(ctx, 0.4) }, "AT+C,-1,-1,0.4,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"skip next point", func(r *robot.Robot) error { return r.SkipNextPoint(ctx) }, "AT+C,-1,-1,-1,-1,-1,-1,1,-1,-1,-1,-1"},
		{"skip to progress", func(r *robot.Robot) error { return r.SkipToProgress(ctx, 0.3) }, "AT+C,-1,-1,-1,-1,-1,0.3,-1,-1,-1,-1,-1"},
		{"reboot", func(r *robot.Robot) error { return r.Reboot(ctx) }, "AT+Y"},
		{"reboot gps", func(r *robot.Robot) error { return r.RebootGPS(ctx) }, "AT+Y2"},
		{"shutdown", func(r *robot.Robot) error { return r.Shutdown(ctx) }, "AT+Y3"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			if err := tt.run(f.robot); err != nil {
				t.Fatal(err)
			}
			if got := f.sender.payloads(); !reflect.DeepEqual(got, []string{tt.want}) {
				t.Errorf("sent %q, want %q", got, tt.want)
			}
		})
	}
}

func TestCommandsUseConfiguredSettings(t *testing.T) {
	sender := newFakeSender()
	cfg := robot.DefaultConfig()
	cfg.MowSpeedMps, cfg.GotoSpeedMps, cfg.FixTimeoutSec, cfg.FinishAndRestart = 0.35, 0.5, 120, true
	cfg.Logger = testkit.Logger(t)
	r := robot.New(sender, cfg)

	_ = r.Mow(context.Background())
	_ = r.Goto(context.Background())
	want := []string{"AT+C,1,1,0.35,120,1,-1,-1,-1,-1,-1,1", "AT+C,0,1,0.5,120,0,-1,-1,-1,-1,-1,0"}
	if got := sender.payloads(); !reflect.DeepEqual(got, want) {
		t.Errorf("sent %q, want %q", got, want)
	}
}

func TestPositionModeOnConnect(t *testing.T) {
	tests := []struct {
		name     string
		absolute bool
		want     string
	}{
		{"relative", false, "AT+P,0,0,0"},
		{"absolute", true, "AT+P,1,13.4,52.5"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			sender := newFakeSender()
			cfg := robot.DefaultConfig()
			cfg.AbsolutePosition = tt.absolute
			if tt.absolute {
				cfg.Lon, cfg.Lat = 13.4, 52.5
			}
			r := robot.New(sender, cfg)

			r.OnOnline(true)
			r.OnOnline(false)
			if got := sender.payloads(); !reflect.DeepEqual(got, []string{tt.want}) {
				t.Errorf("sent %q, want only %q on connect", got, tt.want)
			}
		})
	}
}

func TestPositionModeFailureDoesNotBreakTheConnection(t *testing.T) {
	f := newFixture(t)
	f.sender.fail["AT+P"] = 1
	f.online(state(protocol.OpIdle))
	if s := f.robot.Snapshot().Status; s != robot.StatusIdle {
		t.Errorf("status = %q, want idle", s)
	}
}

func TestFailedCommandReturnsErrorAndChangesNothing(t *testing.T) {
	f := newFixture(t)
	f.online(state(protocol.OpMow))
	f.sender.fail["AT+C"] = 1

	err := f.robot.SetMowMotor(context.Background(), true)
	if !errors.Is(err, errLinkDown) || !strings.Contains(err.Error(), "mow motor") {
		t.Fatalf("err = %v, want link error naming the command", err)
	}
	if s := f.robot.Snapshot(); s.MowMotorOn || s.Status != robot.StatusTransit {
		t.Errorf("after failed command: mow motor %v, status %q; want unchanged", s.MowMotorOn, s.Status)
	}
}

func TestSkipToProgressValidatesFraction(t *testing.T) {
	f := newFixture(t)
	for _, fraction := range []float64{-0.1, 1.01} {
		if err := f.robot.SkipToProgress(context.Background(), fraction); err == nil {
			t.Errorf("SkipToProgress(%v) succeeded, want error", fraction)
		}
	}
	if sent := f.sender.payloads(); len(sent) != 0 {
		t.Errorf("sent %q for invalid fractions", sent)
	}
}

func TestStopRetries(t *testing.T) {
	t.Run("succeeds on third attempt", func(t *testing.T) {
		f := newFixture(t)
		f.sender.fail["AT+C"] = 2
		if err := f.robot.Stop(context.Background()); err != nil {
			t.Fatalf("Stop: %v", err)
		}
		if n := len(f.sender.payloads()); n != 3 {
			t.Errorf("sent %d times, want 3", n)
		}
	})
	t.Run("gives up after three attempts", func(t *testing.T) {
		f := newFixture(t)
		f.sender.fail["AT+C"] = 5
		if err := f.robot.Stop(context.Background()); !errors.Is(err, errLinkDown) {
			t.Fatalf("Stop err = %v, want link error", err)
		}
		if n := len(f.sender.payloads()); n != 3 {
			t.Errorf("sent %d times, want 3", n)
		}
	})
	t.Run("other commands are not repeated", func(t *testing.T) {
		f := newFixture(t)
		f.sender.fail["AT+C"] = 1
		_ = f.robot.SkipNextPoint(context.Background())
		if n := len(f.sender.payloads()); n != 1 {
			t.Errorf("skip sent %d times, want 1", n)
		}
	})
	t.Run("stops retrying when the context ends", func(t *testing.T) {
		f := newFixture(t)
		f.sender.fail["AT+C"] = 5
		ctx, cancel := context.WithCancel(context.Background())
		cancel()
		_ = f.robot.Stop(ctx)
		if n := len(f.sender.payloads()); n != 1 {
			t.Errorf("sent %d times with cancelled context, want 1", n)
		}
	})
}

func TestStopSwitchesOffMowMotorAndManualMove(t *testing.T) {
	f := newFixture(t)
	f.online(state(protocol.OpIdle))
	_ = f.robot.SetMowMotor(context.Background(), true)
	_ = f.robot.Move(context.Background(), 0.3, 0)

	_ = f.robot.Stop(context.Background())
	if s := f.robot.Snapshot(); s.MowMotorOn || s.Status != robot.StatusIdle {
		t.Errorf("after stop: mow motor %v, status %q; want off / idle", s.MowMotorOn, s.Status)
	}
}

var square = protocol.Map{
	Perimeter: pts(0, 0, 10, 0, 10, 10, 0, 10),
	Dock:      pts(0, 1, 0, -2),
	Way:       make([]geo.Point, 40), // two AT+W packets
}

func TestUploadMap(t *testing.T) {
	f := newFixture(t)
	if err := f.robot.UploadMap(context.Background(), square); err != nil {
		t.Fatal(err)
	}
	sent := f.sender.payloads()
	want := protocol.MapUpload(square)
	if !reflect.DeepEqual(sent, want) {
		t.Errorf("sent %d messages, want the %d from protocol.MapUpload", len(sent), len(want))
	}
}

func TestUploadMapChecksAcks(t *testing.T) {
	t.Run("robot stored fewer points", func(t *testing.T) {
		f := newFixture(t)
		f.sender.replies["AT+W"] = "W,12"
		err := f.robot.UploadMap(context.Background(), square)
		if !errors.Is(err, robot.ErrUploadRejected) {
			t.Errorf("err = %v, want ErrUploadRejected", err)
		}
	})
	t.Run("malformed ack", func(t *testing.T) {
		f := newFixture(t)
		f.sender.replies["AT+W"] = "W,x"
		if err := f.robot.UploadMap(context.Background(), square); !errors.Is(err, protocol.ErrMalformed) {
			t.Errorf("err = %v, want ErrMalformed", err)
		}
	})
	t.Run("links without replies are not checked", func(t *testing.T) {
		f := newFixture(t)
		f.sender.replies["AT+W"] = ""
		if err := f.robot.UploadMap(context.Background(), square); err != nil {
			t.Errorf("err = %v, want nil", err)
		}
	})
	t.Run("send error", func(t *testing.T) {
		f := newFixture(t)
		f.sender.fail["AT+N"] = 1
		if err := f.robot.UploadMap(context.Background(), square); !errors.Is(err, errLinkDown) {
			t.Errorf("err = %v, want link error", err)
		}
	})
}

func TestStopAbortsMapUpload(t *testing.T) {
	f := newFixture(t)
	f.online(state(protocol.OpIdle))
	f.sender.block["AT+W"] = true

	done := make(chan error, 1)
	go func() { done <- f.robot.UploadMap(context.Background(), square) }()
	<-f.sender.blocked

	if s := f.robot.Snapshot().Status; s != robot.StatusMapUpload {
		t.Errorf("status during upload = %q, want map upload", s)
	}

	f.sender.mu.Lock()
	f.sender.block["AT+W"] = false
	f.sender.mu.Unlock()
	if err := f.robot.Stop(context.Background()); err != nil {
		t.Fatalf("Stop: %v", err)
	}

	select {
	case err := <-done:
		if !errors.Is(err, context.Canceled) {
			t.Errorf("upload err = %v, want context.Canceled", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("upload did not end after Stop")
	}
	sent := f.sender.payloads()
	if last := sent[len(sent)-1]; last != protocol.Stop().Encode() {
		t.Errorf("last payload = %q, want stop", last)
	}
	if s := f.robot.Snapshot().Status; s != robot.StatusIdle {
		t.Errorf("status after abort = %q, want idle", s)
	}
}

func TestCommandsWaitForUpload(t *testing.T) {
	f := newFixture(t)
	f.sender.block["AT+W"] = true

	uploadCtx, cancelUpload := context.WithCancel(context.Background())
	uploaded := make(chan error, 1)
	go func() { uploaded <- f.robot.UploadMap(uploadCtx, square) }()
	<-f.sender.blocked

	mowed := make(chan error, 1)
	go func() { mowed <- f.robot.Mow(context.Background()) }()
	select {
	case <-mowed:
		t.Fatal("mow was sent while the map upload was still running")
	case <-time.After(50 * time.Millisecond):
	}

	cancelUpload()
	<-uploaded
	if err := <-mowed; err != nil {
		t.Errorf("mow after upload: %v", err)
	}
}

func TestUploadMapWaitsForChecksum(t *testing.T) {
	want := protocol.MapChecksum(square)
	report := func(crc int64) func(f fixture) {
		return func(f fixture) {
			s := state(protocol.OpIdle)
			s.MapCRC = crc
			f.robot.OnState(s)
		}
	}
	tests := []struct {
		name    string
		after   func(f fixture) // runs while UploadMap waits
		wantErr error
	}{
		{"linux checksum", report(want.Linux), nil},
		{"arduino checksum", report(want.Arduino), nil},
		{"other map stays on the robot", report(want.Linux + 1), robot.ErrMapCRCMismatch},
		{"no state report", func(fixture) {}, robot.ErrMapCRCMismatch},
		{"stop", func(f fixture) { _ = f.robot.Stop(context.Background()) }, context.Canceled},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			f.sender.stored = nil // the robot reports nothing by itself
			done := make(chan error, 1)
			go func() { done <- f.robot.UploadMap(context.Background(), square) }()
			waitFor(t, func() bool { return len(f.sender.payloads()) == len(protocol.MapUpload(square)) })
			tt.after(f)
			if err := <-done; !errors.Is(err, tt.wantErr) {
				t.Errorf("err = %v, want %v", err, tt.wantErr)
			}
			uploaded := len(f.robot.Map().Perimeter) > 0
			if uploaded != (tt.wantErr == nil) {
				t.Errorf("map stored as uploaded = %v, want %v", uploaded, tt.wantErr == nil)
			}
		})
	}
}

func TestUploadMapAcceptsMatchingChecksumAlreadyReported(t *testing.T) {
	f := newFixture(t)
	f.sender.stored = nil
	s := state(protocol.OpIdle)
	s.MapCRC = protocol.MapChecksum(square).Linux // e.g. the same map uploaded again
	f.online(s)
	if err := f.robot.UploadMap(context.Background(), square); err != nil {
		t.Fatal(err)
	}
}

func waitFor(t *testing.T, ok func() bool) {
	t.Helper()
	deadline := time.Now().Add(2 * time.Second)
	for !ok() {
		if time.Now().After(deadline) {
			t.Fatal("condition not met in time")
		}
		time.Sleep(time.Millisecond)
	}
}

func TestUploadMapRefusedWhileDriving(t *testing.T) {
	for _, op := range []protocol.Op{protocol.OpMow, protocol.OpDock} {
		t.Run(op.String(), func(t *testing.T) {
			f := newFixture(t)
			f.online(state(op))
			err := f.robot.UploadMap(context.Background(), square)
			if !errors.Is(err, robot.ErrBusy) {
				t.Errorf("err = %v, want ErrBusy", err)
			}
			for _, p := range f.sender.payloads() {
				if strings.HasPrefix(p, "AT+W") {
					t.Fatalf("sent %q while the robot drives", p)
				}
			}
		})
	}
	t.Run("manual driving", func(t *testing.T) {
		f := newFixture(t)
		f.online(state(protocol.OpIdle))
		if err := f.robot.Move(context.Background(), 0.2, 0); err != nil {
			t.Fatal(err)
		}
		if err := f.robot.UploadMap(context.Background(), square); !errors.Is(err, robot.ErrBusy) {
			t.Errorf("err = %v, want ErrBusy", err)
		}
	})
}

func TestSetSettingsApplyToTheNextCommand(t *testing.T) {
	f := newFixture(t)
	s := robot.DefaultConfig().Settings
	s.MowSpeedMps, s.FixTimeoutSec, s.FinishAndRestart = 0.5, 30, true
	s.GotoSpeedMps = 0.6
	f.robot.SetSettings(s)
	if err := f.robot.Mow(context.Background()); err != nil {
		t.Fatal(err)
	}
	if err := f.robot.Goto(context.Background()); err != nil {
		t.Fatal(err)
	}
	sent := f.sender.payloads()
	want := []string{protocol.Mow(0.5, 30, true).Encode(), protocol.Goto(0.6, 30).Encode()}
	if !reflect.DeepEqual(sent, want) {
		t.Errorf("sent %q, want %q", sent, want)
	}
}

func TestSendPositionMode(t *testing.T) {
	f := newFixture(t)
	s := robot.DefaultConfig().Settings
	s.AbsolutePosition, s.Lon, s.Lat = true, 13.4, 52.5
	f.robot.SetSettings(s)
	if err := f.robot.SendPositionMode(context.Background()); err != nil {
		t.Fatal(err)
	}
	if sent := f.sender.payloads(); len(sent) != 1 || sent[0] != protocol.PositionMode(true, 13.4, 52.5) {
		t.Errorf("sent %q", sent)
	}
	f.sender.fail["AT+P"] = 1
	if err := f.robot.SendPositionMode(context.Background()); !errors.Is(err, errLinkDown) {
		t.Errorf("err = %v, want the link error", err)
	}
}
