package stats

import (
	"context"
	"log/slog"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
)

// Robot is what the recorder reads.
type Robot interface {
	Snapshot() robot.Snapshot
}

// Config holds the injectable parts of a Recorder.
type Config struct {
	Now func() time.Time
	// Interval between two samples (default one minute).
	Interval time.Duration
	// Retention is how long samples are kept (default one year); the hourly
	// totals are kept for good.
	Retention time.Duration
	Logger    *slog.Logger
}

// Recorder writes a sample of the robot every Interval while it reports, and
// the growth of its counters whenever it sent new ones.
type Recorder struct {
	store *Store
	robot Robot
	cfg   Config
	log   *slog.Logger

	statsAt  time.Time // of the last counters written
	prunedAt time.Time
}

// NewRecorder returns a recorder; Run starts it.
func NewRecorder(store *Store, r Robot, cfg Config) *Recorder {
	if cfg.Now == nil {
		cfg.Now = time.Now
	}
	if cfg.Interval <= 0 {
		cfg.Interval = time.Minute
	}
	if cfg.Retention <= 0 {
		cfg.Retention = 365 * 24 * time.Hour
	}
	if cfg.Logger == nil {
		cfg.Logger = slog.New(slog.DiscardHandler)
	}
	return &Recorder{store: store, robot: r, cfg: cfg, log: cfg.Logger}
}

// Run records every Interval until ctx ends.
func (r *Recorder) Run(ctx context.Context) {
	t := time.NewTicker(r.cfg.Interval)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			r.Record(ctx)
		}
	}
}

// Record writes what is new since the last call. Errors are logged: a
// missing sample must not stop the app.
func (r *Recorder) Record(ctx context.Context) {
	now := r.cfg.Now()
	snap := r.robot.Snapshot()
	// Only fresh reports: an offline robot keeps its last values.
	if snap.Online && !snap.UpdatedAt.IsZero() && now.Sub(snap.UpdatedAt) < 2*r.cfg.Interval {
		err := r.store.AddSample(ctx, Sample{
			T:             now.Truncate(time.Second),
			BatteryV:      snap.BatteryV,
			Amps:          snap.Amps,
			Satellites:    float64(snap.Satellites),
			AccuracyM:     snap.AccuracyM,
			LateralErrorM: snap.LateralErrorM,
		})
		if err != nil && ctx.Err() == nil {
			r.log.Error("stats", "err", err)
		}
	}
	if !snap.StatsAt.IsZero() && !snap.StatsAt.Equal(r.statsAt) {
		if err := r.store.AddStats(ctx, now, snap.Stats); err != nil {
			if ctx.Err() == nil {
				r.log.Error("stats", "err", err)
			}
		} else {
			r.statsAt = snap.StatsAt
		}
	}
	if now.Sub(r.prunedAt) >= 24*time.Hour {
		if err := r.store.Prune(ctx, now.Add(-r.cfg.Retention)); err != nil && ctx.Err() == nil {
			r.log.Error("stats", "err", err)
		}
		r.prunedAt = now
	}
}
