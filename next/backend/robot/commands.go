package robot

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// stopAttempts: Stop is the only command that is repeated on failure. It is
// idempotent and the most important one to get through.
const stopAttempts = 3

// Stop stops all motors. It cancels a command in flight (e.g. a map upload)
// instead of waiting for it.
func (r *Robot) Stop(ctx context.Context) error {
	r.mu.Lock()
	if r.cancelBusy != nil {
		r.cancelBusy()
	}
	r.mowMotor = false
	r.moveUntil = r.cfg.Now()
	r.mu.Unlock()

	r.log.Info("command", "cmd", "stop")
	var err error
	for range stopAttempts {
		if _, err = r.link.Send(ctx, protocol.Stop().Encode()); err == nil || ctx.Err() != nil {
			break
		}
		r.log.Warn("stop failed, retrying", "err", err)
	}
	if err != nil {
		return fmt.Errorf("stop: %w", err)
	}
	return nil
}

// Dock drives to the docking station, sent home by the user.
func (r *Robot) Dock(ctx context.Context) error {
	return r.DockFor(ctx, DockReasonUser)
}

// DockFor drives to the docking station; reason is reported while docking.
func (r *Robot) DockFor(ctx context.Context, reason DockReason) error {
	// Mark before sending: the first docking state may arrive before Send returns.
	r.mu.Lock()
	r.dockAsked = reason
	r.mu.Unlock()
	err := r.command(ctx, "dock", protocol.Dock().Encode(), func() { r.mowMotor = false })
	if err != nil {
		r.mu.Lock()
		r.dockAsked = DockReasonNone
		r.mu.Unlock()
	}
	return err
}

// Mow starts mowing the uploaded route.
func (r *Robot) Mow(ctx context.Context) error {
	s := r.settings()
	cmd := protocol.Mow(s.MowSpeedMps, s.FixTimeoutSec, s.FinishAndRestart)
	return r.command(ctx, "mow", cmd.Encode(), func() { r.mowMotor = true })
}

// Goto drives along the uploaded route with the mow motor off.
func (r *Robot) Goto(ctx context.Context) error {
	s := r.settings()
	cmd := protocol.Goto(s.GotoSpeedMps, s.FixTimeoutSec)
	return r.command(ctx, "goto", cmd.Encode(), func() { r.mowMotor = false })
}

// Move drives manually (joystick). Move(ctx, 0, 0) stops.
func (r *Robot) Move(ctx context.Context, linearMps, angularRadps float64) error {
	return r.command(ctx, "move", protocol.Move(linearMps, angularRadps), func() {
		r.moveUntil = r.cfg.Now()
		if linearMps != 0 || angularRadps != 0 {
			r.moveUntil = r.moveUntil.Add(manualMoveHold)
		}
	})
}

// SetMowMotor switches the mow motor on or off.
func (r *Robot) SetMowMotor(ctx context.Context, on bool) error {
	return r.command(ctx, "mow motor", protocol.MowMotor(on).Encode(), func() { r.mowMotor = on })
}

// SetSpeed changes the speed of the running operation.
func (r *Robot) SetSpeed(ctx context.Context, mps float64) error {
	return r.command(ctx, "speed", protocol.Speed(mps).Encode(), nil)
}

// SkipNextPoint continues with the next mow point.
func (r *Robot) SkipNextPoint(ctx context.Context) error {
	return r.command(ctx, "skip next point", protocol.SkipNextPoint().Encode(), nil)
}

// SkipToProgress continues at a fraction (0..1) of the route.
func (r *Robot) SkipToProgress(ctx context.Context, fraction float64) error {
	if fraction < 0 || fraction > 1 {
		return fmt.Errorf("skip to progress: fraction %v not in 0..1", fraction)
	}
	return r.command(ctx, "skip to progress", protocol.SkipToProgress(fraction).Encode(), nil)
}

// Reboot restarts the robot.
func (r *Robot) Reboot(ctx context.Context) error {
	return r.command(ctx, "reboot", protocol.Reboot, nil)
}

// RebootGPS restarts the GPS receiver.
func (r *Robot) RebootGPS(ctx context.Context) error {
	return r.command(ctx, "reboot gps", protocol.RebootGPS, nil)
}

// Shutdown switches the robot off.
func (r *Robot) Shutdown(ctx context.Context) error {
	return r.command(ctx, "shutdown", protocol.Shutdown, nil)
}

// ErrUploadRejected means the robot did not accept all map points.
var ErrUploadRejected = errors.New("map upload rejected")

// ErrBusy means the robot is driving; a map upload would replace the route
// it is following (AT+W with index 0 clears the robot's map).
var ErrBusy = errors.New("robot is driving, stop it first")

// ErrMapCRCMismatch means the robot did not report the checksum of the
// uploaded map in time, so it stores a different map.
var ErrMapCRCMismatch = errors.New("map checksum mismatch")

// UploadMap transfers m to the robot and waits until the robot reports its
// checksum. Stop aborts a running upload.
func (r *Robot) UploadMap(ctx context.Context, m protocol.Map) error {
	r.cmdMu.Lock()
	defer r.cmdMu.Unlock()

	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	r.mu.Lock()
	switch st := r.statusLocked(); st {
	case StatusMow, StatusTransit, StatusDocking, StatusMove:
		r.mu.Unlock()
		return fmt.Errorf("upload map: %w (status %s)", ErrBusy, st)
	}
	r.cancelBusy = cancel
	r.uploading = true
	r.mu.Unlock()
	defer func() {
		r.mu.Lock()
		r.cancelBusy = nil
		r.uploading = false
		r.mu.Unlock()
	}()

	msgs := protocol.MapUpload(m)
	r.log.Info("command", "cmd", "upload map", "messages", len(msgs))
	next := 0
	for _, msg := range msgs {
		reply, err := r.link.Send(ctx, msg)
		if err != nil {
			return fmt.Errorf("upload map: %w", err)
		}
		if !strings.HasPrefix(msg, "AT+W,") || reply == "" { // links without replies cannot be checked
			continue
		}
		got, err := protocol.ParseWaypointAck(reply)
		if err != nil {
			return fmt.Errorf("upload map: %w", err)
		}
		next += (strings.Count(msg, ",") - 1) / 2
		if got != next {
			return fmt.Errorf("upload map: %w: robot stored up to point %d, sent %d", ErrUploadRejected, got, next)
		}
	}
	if err := r.awaitMapCRC(ctx, protocol.MapChecksum(m)); err != nil {
		return fmt.Errorf("upload map: %w", err)
	}
	r.mu.Lock()
	r.uploaded = m
	r.mu.Unlock()
	return nil
}

// awaitMapCRC waits for a state report with the expected map checksum.
// It is the only check that also works for links without replies (MQTT).
func (r *Robot) awaitMapCRC(ctx context.Context, want protocol.MapCRC) error {
	timeout := time.NewTimer(r.cfg.MapCRCTimeout)
	defer timeout.Stop()
	for {
		r.mu.Lock()
		got, seen := r.state.MapCRC, r.stateSeen
		r.mu.Unlock()
		if want.Matches(got) {
			return nil
		}
		select {
		case <-seen:
		case <-ctx.Done():
			return ctx.Err()
		case <-timeout.C:
			return fmt.Errorf("%w: robot reports %d, want %d (Arduino) or %d (Linux)",
				ErrMapCRCMismatch, got, want.Arduino, want.Linux)
		}
	}
}

// command sends one command and, if it was delivered, applies its effect
// on the tracked state.
func (r *Robot) command(ctx context.Context, name, payload string, apply func()) error {
	r.cmdMu.Lock()
	defer r.cmdMu.Unlock()
	r.log.Info("command", "cmd", name)
	if _, err := r.link.Send(ctx, payload); err != nil {
		return fmt.Errorf("%s: %w", name, err)
	}
	if apply != nil {
		r.mu.Lock()
		apply()
		r.mu.Unlock()
	}
	return nil
}
