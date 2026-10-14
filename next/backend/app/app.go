// Package app wires all features together and runs CaSSAndRA.
package app

import (
	"context"
	"errors"
	"fmt"
	"io/fs"
	"log/slog"
	"net"
	"net/http"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/server"
)

const shutdownTimeout = 5 * time.Second

// Config holds everything the app needs to start.
type Config struct {
	Version string
	UI      fs.FS
	Logger  *slog.Logger
	Robot   robot.Config
	// SimTick is the simulation step; the simulator is the only link so far.
	SimTick time.Duration
	// Poll controls how often the robot is asked for data.
	Poll link.PollConfig
	// PublishInterval is how often the browser gets state updates (if changed).
	PublishInterval time.Duration
	// Heartbeat keeps idle event streams open through proxies.
	Heartbeat time.Duration
}

// DefaultConfig returns the settings for running with the simulator.
func DefaultConfig() Config {
	poll := link.DefaultPollConfig()
	poll.StateInterval = 200 * time.Millisecond // the simulator is local and cheap
	return Config{
		Robot:           robot.DefaultConfig(),
		SimTick:         100 * time.Millisecond,
		Poll:            poll,
		PublishInterval: 200 * time.Millisecond,
		Heartbeat:       15 * time.Second,
	}
}

// validate rejects settings that would make loops spin or panic.
func (c Config) validate() error {
	for name, d := range map[string]time.Duration{
		"SimTick": c.SimTick, "Poll.StateInterval": c.Poll.StateInterval,
		"Poll.ObstaclesInterval": c.Poll.ObstaclesInterval, "Poll.StatsInterval": c.Poll.StatsInterval,
		"Poll.ReconnectDelay": c.Poll.ReconnectDelay, "PublishInterval": c.PublishInterval,
		"Heartbeat": c.Heartbeat, "Robot.OfflineAfter": c.Robot.OfflineAfter,
	} {
		if d <= 0 {
			return fmt.Errorf("invalid config: %s must be positive, got %v (start from DefaultConfig)", name, d)
		}
	}
	return nil
}

// Run serves CaSSAndRA on ln until ctx is cancelled, then shuts down gracefully.
func Run(ctx context.Context, cfg Config, ln net.Listener) error {
	if err := cfg.validate(); err != nil {
		return err
	}
	if cfg.Logger == nil {
		cfg.Logger = slog.New(slog.DiscardHandler)
	}
	log := cfg.Logger
	cfg.Robot.Logger = log.With("feature", "robot")

	// Deferred in reverse: first cancel the background goroutines, then wait for them.
	var wg sync.WaitGroup
	defer wg.Wait()
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	goroutine := func(f func()) {
		wg.Add(1)
		go func() {
			defer wg.Done()
			f()
		}()
	}

	simCfg := link.DefaultSimConfig()
	simCfg.Start = link.DemoStation
	sim := link.NewSim(simCfg)
	poller := link.NewPoller(sim, cfg.Poll)
	r := robot.New(poller, cfg.Robot)
	hub := server.NewHub(cfg.Heartbeat)

	goroutine(func() { sim.Run(ctx, cfg.SimTick) })
	goroutine(func() {
		if err := poller.Run(ctx, r); err != nil {
			log.Error("robot link stopped", "err", err)
		}
	})
	goroutine(func() { r.PublishState(ctx, cfg.PublishInterval, func(b []byte) { hub.Publish("robot", b) }) })
	goroutine(func() { uploadDemoMap(ctx, r, log) })

	srv := &http.Server{
		Handler: server.New(server.Options{
			Version: cfg.Version,
			UI:      cfg.UI,
			Logger:  log,
			Events:  hub,
			Routes:  map[string]http.Handler{"/api/robot/": r.Handler()},
		}),
		ReadHeaderTimeout: 5 * time.Second,
		// Requests end with the app, so open event streams do not block shutdown.
		BaseContext: func(net.Listener) context.Context { return ctx },
	}

	serveErr := make(chan error, 1)
	go func() { serveErr <- srv.Serve(ln) }()
	log.Info("CaSSAndRA started", "addr", ln.Addr().String(), "version", cfg.Version, "link", "simulator")

	select {
	case err := <-serveErr:
		return fmt.Errorf("serve http: %w", err)
	case <-ctx.Done():
	}

	log.Info("shutting down")
	shutdownCtx, cancelShutdown := context.WithTimeout(context.WithoutCancel(ctx), shutdownTimeout)
	defer cancelShutdown()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("shutdown http: %w", err)
	}
	if err := <-serveErr; !errors.Is(err, http.ErrServerClosed) {
		return fmt.Errorf("serve http: %w", err)
	}
	return nil
}

// uploadDemoMap gives the simulated robot something to mow once it is online.
func uploadDemoMap(ctx context.Context, r *robot.Robot, log *slog.Logger) {
	t := time.NewTicker(100 * time.Millisecond)
	defer t.Stop()
	for !r.Snapshot().Online {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
		}
	}
	if err := r.UploadMap(ctx, link.DemoMap()); err != nil && ctx.Err() == nil {
		log.Error("upload demo map", "err", err)
	}
}
