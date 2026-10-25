package robot

import (
	"context"
	"fmt"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// OnOnline implements link.Handler. On every new connection the robot gets
// the configured position mode, like legacy CaSSAndRA does.
func (r *Robot) OnOnline(online bool) {
	r.mu.Lock()
	r.online = online
	r.mu.Unlock()
	r.log.Info("robot connection", "online", online)
	if !online {
		return
	}
	if err := r.SendPositionMode(context.Background()); err != nil {
		r.log.Warn("set position mode", "err", err)
	}
}

// SendPositionMode sends the configured position mode (AT+P). It does not
// wait for other commands: OnOnline calls it from the link's loop, which
// must keep delivering states while e.g. a map upload waits for its checksum.
func (r *Robot) SendPositionMode(ctx context.Context) error {
	s := r.settings()
	r.log.Info("command", "cmd", "position mode", "absolute", s.AbsolutePosition)
	if _, err := r.link.Send(ctx, protocol.PositionMode(s.AbsolutePosition, s.Lon, s.Lat)); err != nil {
		return fmt.Errorf("position mode: %w", err)
	}
	return nil
}

// OnVersion implements link.Handler.
func (r *Robot) OnVersion(v protocol.Version) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.version = v
}

// OnState implements link.Handler.
func (r *Robot) OnState(s protocol.State) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if s.Op != r.state.Op && (s.Op == protocol.OpDock || s.Op == protocol.OpCharge || s.Op == protocol.OpError) {
		r.mowMotor = false // the firmware switches it off
	}
	r.updateDockReasonLocked(s)
	before := r.statusLocked()
	r.state = s
	r.stateAt = r.cfg.Now()
	r.updateTrailLocked(before, r.statusLocked())
	close(r.stateSeen)
	r.stateSeen = make(chan struct{})
}

// OnStats implements link.Handler.
func (r *Robot) OnStats(s protocol.Stats) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.stats = s
	r.statsAt = r.cfg.Now()
}

// OnObstacles implements link.Handler.
func (r *Robot) OnObstacles(o [][]geo.Point) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.obstacles = o
}

// ClearObstacles forgets the obstacles until the robot reports them again
// (legacy "resetObstacles" only clears the display).
func (r *Robot) ClearObstacles() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.obstacles = nil
}
