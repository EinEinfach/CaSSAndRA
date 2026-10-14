// Package robot tracks the robot state and issues commands to it.
package robot

import (
	"context"
	"log/slog"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// Sender delivers one request payload to the robot and returns the reply
// payload. link.Link implements it.
type Sender interface {
	Send(ctx context.Context, payload string) (string, error)
}

// Config holds the user settings the robot needs.
type Config struct {
	MowSpeedMps      float64
	GotoSpeedMps     float64
	FixTimeoutSec    int
	FinishAndRestart bool
	// AbsolutePosition uses Lon/Lat as reference point instead of relative positioning.
	AbsolutePosition bool
	Lon, Lat         float64
	// Battery voltages for 0 % and 100 % state of charge.
	BatteryEmptyV, BatteryFullV float64
	// ChargingBelowA: a docked robot is charging while amps are at or below this.
	ChargingBelowA float64
	// OfflineAfter without a state report the robot counts as offline.
	OfflineAfter time.Duration
	// Now returns the current time; tests pass a fake clock.
	Now func() time.Time
	// Logger receives command and connection events.
	Logger *slog.Logger
}

// DefaultConfig returns the legacy CaSSAndRA defaults.
func DefaultConfig() Config {
	return Config{
		MowSpeedMps:    0.25,
		GotoSpeedMps:   0.3,
		FixTimeoutSec:  60,
		BatteryEmptyV:  22,
		BatteryFullV:   28,
		ChargingBelowA: -0.03,
		OfflineAfter:   60 * time.Second,
	}
}

// Robot is the CaSSAndRA view of one robot. It implements link.Handler to
// receive reports and sends commands through a Sender. Safe for concurrent use.
type Robot struct {
	link Sender
	cfg  Config
	log  *slog.Logger

	// cmdMu serializes commands. Stop does not take it; it cancels the
	// command in flight instead, so it never waits behind a map upload.
	cmdMu sync.Mutex

	mu         sync.Mutex
	online     bool
	version    protocol.Version
	state      protocol.State
	stateAt    time.Time
	stats      protocol.Stats
	obstacles  [][]geo.Point
	mowMotor   bool // last commanded; the robot does not report it
	moveUntil  time.Time
	uploading  bool
	dockByUser bool
	dockReason DockReason
	cancelBusy context.CancelFunc
}

// New returns a Robot that sends commands through l.
func New(l Sender, cfg Config) *Robot {
	if cfg.Now == nil {
		cfg.Now = time.Now
	}
	if cfg.Logger == nil {
		cfg.Logger = slog.New(slog.DiscardHandler)
	}
	return &Robot{link: l, cfg: cfg, log: cfg.Logger}
}
