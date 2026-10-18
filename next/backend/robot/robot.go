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

// Settings are the user settings the robot needs. They can change while
// the robot runs (SetSettings).
type Settings struct {
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
}

// Config holds everything the robot needs at start.
type Config struct {
	Settings
	// MapCRCTimeout is how long UploadMap waits for the robot to report the
	// checksum of the new map.
	MapCRCTimeout time.Duration
	// Now returns the current time; tests pass a fake clock.
	Now func() time.Time
	// Logger receives command and connection events.
	Logger *slog.Logger
}

// DefaultConfig returns the legacy CaSSAndRA defaults.
func DefaultConfig() Config {
	return Config{
		Settings: Settings{
			MowSpeedMps:    0.25,
			GotoSpeedMps:   0.3,
			FixTimeoutSec:  60,
			BatteryEmptyV:  22,
			BatteryFullV:   28,
			ChargingBelowA: -0.03,
			OfflineAfter:   60 * time.Second,
		},
		MapCRCTimeout: 10 * time.Second,
	}
}

// Robot is the CaSSAndRA view of one robot. It implements link.Handler to
// receive reports and sends commands through a Sender. Safe for concurrent use.
type Robot struct {
	link Sender
	cfg  Config // cfg.Settings is guarded by mu
	log  *slog.Logger

	// cmdMu serializes commands. Stop does not take it; it cancels the
	// command in flight instead, so it never waits behind a map upload.
	cmdMu sync.Mutex

	mu         sync.Mutex
	online     bool
	version    protocol.Version
	state      protocol.State
	stateAt    time.Time
	stateSeen  chan struct{} // closed and replaced on every state report
	stats      protocol.Stats
	obstacles  [][]geo.Point
	mowMotor   bool // last commanded; the robot does not report it
	moveUntil  time.Time
	uploading  bool
	dockByUser bool
	dockReason DockReason
	cancelBusy context.CancelFunc
	uploaded   protocol.Map
	trail      trail
}

// New returns a Robot that sends commands through l.
func New(l Sender, cfg Config) *Robot {
	if cfg.Now == nil {
		cfg.Now = time.Now
	}
	if cfg.Logger == nil {
		cfg.Logger = slog.New(slog.DiscardHandler)
	}
	r := &Robot{link: l, cfg: cfg, log: cfg.Logger, stateSeen: make(chan struct{})}
	// Ids differ between runs, so a browser never mistakes a new trail for its old one.
	r.trail.id = cfg.Now().UnixMilli()
	return r
}

// SetSettings replaces the user settings. They apply to the next command; a
// changed position mode is sent with the next SendPositionMode.
func (r *Robot) SetSettings(s Settings) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.cfg.Settings = s
}

func (r *Robot) settings() Settings {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.cfg.Settings
}
