package robot

import (
	"context"

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
	cmd := protocol.PositionMode(r.cfg.AbsolutePosition, r.cfg.Lon, r.cfg.Lat)
	if _, err := r.link.Send(context.Background(), cmd); err != nil {
		r.log.Warn("set position mode", "err", err)
	}
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
	r.state = s
	r.stateAt = r.cfg.Now()
}

// OnStats implements link.Handler.
func (r *Robot) OnStats(s protocol.Stats) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.stats = s
}

// OnObstacles implements link.Handler.
func (r *Robot) OnObstacles(o [][]geo.Point) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.obstacles = o
}
