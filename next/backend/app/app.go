// Package app wires all features together and runs CaSSAndRA.
package app

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"log/slog"
	"net"
	"net/http"
	"path/filepath"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/server"
	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

const (
	shutdownTimeout = 5 * time.Second
	// positionModeTimeout bounds sending a changed position mode.
	positionModeTimeout = 5 * time.Second
)

// Config holds everything the app needs to start. The user settings
// (connection, rover, ...) live in DataDir and are changed in the UI.
type Config struct {
	Version string
	UI      fs.FS
	Logger  *slog.Logger
	// DataDir holds settings and maps. On the first start, legacy CaSSAndRA
	// data in the same directory (user/, map/) is imported.
	DataDir string
	// Robot holds the robot defaults; the user settings replace its Settings.
	Robot robot.Config
	// SimTick is the simulation step of the simulated robot.
	SimTick time.Duration
	// Poll controls how often the robot is asked for data.
	Poll link.PollConfig
	// PublishInterval is how often the browser gets state updates (if changed).
	PublishInterval time.Duration
	// Heartbeat keeps idle event streams open through proxies.
	Heartbeat time.Duration
}

// DefaultConfig returns the defaults; only DataDir must be set.
func DefaultConfig() Config {
	return Config{
		Robot:           robot.DefaultConfig(),
		SimTick:         100 * time.Millisecond,
		Poll:            link.DefaultPollConfig(),
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
		"Heartbeat": c.Heartbeat, "Robot.MapCRCTimeout": c.Robot.MapCRCTimeout,
	} {
		if d <= 0 {
			return fmt.Errorf("invalid config: %s must be positive, got %v (start from DefaultConfig)", name, d)
		}
	}
	if c.DataDir == "" {
		return errors.New("invalid config: DataDir must be set")
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

	settingsStore, mapStore, err := openData(cfg.DataDir, log)
	if err != nil {
		return err
	}

	// Deferred in reverse: cancel the background goroutines, then wait for them.
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

	sender := &switchSender{}
	robotCfg := cfg.Robot
	robotCfg.Settings = robotSettings(settingsStore.Get())
	robotCfg.Logger = log.With("feature", "robot")
	r := robot.New(sender, robotCfg)
	hub := server.NewHub(cfg.Heartbeat)

	// The browser follows the settings it shows everywhere (e.g. the robot picture).
	publishSettings := func(s settings.Settings) {
		if b, err := json.Marshal(settings.ViewOf(s)); err == nil {
			hub.Publish("settings", b)
		}
	}
	publishSettings(settingsStore.Get())

	reconnect := make(chan struct{}, 1)
	settingsStore.OnChange(func(old, next settings.Settings) {
		publishSettings(next)
		r.SetSettings(robotSettings(next))
		if old.Rover.AbsolutePosition != next.Rover.AbsolutePosition || old.Rover.Lon != next.Rover.Lon || old.Rover.Lat != next.Rover.Lat {
			pctx, cancel := context.WithTimeout(ctx, positionModeTimeout)
			if err := r.SendPositionMode(pctx); err != nil && !errors.Is(err, link.ErrOffline) {
				log.Warn("send changed position mode", "err", err)
			}
			cancel()
		}
		if old.Connection != next.Connection {
			select {
			case reconnect <- struct{}{}:
			default: // a reconnect is pending anyway
			}
		}
	})
	publishMaps := func() {
		if b, err := json.Marshal(mapStore.ListJSON()); err == nil {
			hub.Publish("maps", b)
		}
	}
	publishMaps()
	mapStore.OnChange(publishMaps)

	goroutine(func() { superviseLink(ctx, cfg, settingsStore, r, sender, reconnect) })
	goroutine(func() { r.PublishState(ctx, cfg.PublishInterval, func(b []byte) { hub.Publish("robot", b) }) })

	mapsAPI := mapStore.Handler(r)
	srv := &http.Server{
		Handler: server.New(server.Options{
			Version: cfg.Version,
			UI:      cfg.UI,
			Logger:  log,
			Events:  hub,
			Routes: map[string]http.Handler{
				"/api/robot/":   r.Handler(),
				"/api/settings": settingsStore.Handler(),
				"/api/maps":     mapsAPI,
				"/api/maps/":    mapsAPI,
			},
		}),
		ReadHeaderTimeout: 5 * time.Second,
		// Requests end with the app, so open event streams do not block shutdown.
		BaseContext: func(net.Listener) context.Context { return ctx },
	}

	serveErr := make(chan error, 1)
	go func() { serveErr <- srv.Serve(ln) }()
	log.Info("CaSSAndRA started", "addr", ln.Addr().String(), "version", cfg.Version, "data", cfg.DataDir)

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

// openData opens settings and maps. On the first start it imports the data
// of legacy CaSSAndRA from the same directory.
func openData(dir string, log *slog.Logger) (*settings.Store, *maps.Store, error) {
	settingsStore, err := settings.Open(filepath.Join(dir, "settings.json"))
	if err != nil {
		return nil, nil, err
	}
	if !settingsStore.Exists() {
		s, found, warnings, err := settings.ImportLegacy(filepath.Join(dir, "user"))
		if err != nil {
			return nil, nil, err
		}
		for _, w := range warnings {
			log.Warn("legacy settings import", "problem", w)
		}
		if err := settingsStore.Set(s); err != nil {
			return nil, nil, err
		}
		log.Info("settings created", "importedFromLegacy", found)
	}

	mapStore, err := maps.OpenStore(filepath.Join(dir, "maps"), maps.StoreConfig{})
	if err != nil {
		return nil, nil, err
	}
	if mapStore.Fresh() {
		li, err := maps.ImportLegacy(filepath.Join(dir, "map"))
		if err != nil {
			log.Warn("legacy maps import", "err", err)
		}
		n, warnings := mapStore.Import(li)
		for _, w := range warnings {
			log.Warn("legacy maps import", "problem", w)
		}
		if n > 0 {
			log.Info("legacy maps imported", "maps", n, "active", li.Active)
		}
	}
	return settingsStore, mapStore, nil
}

func robotSettings(s settings.Settings) robot.Settings {
	return robot.Settings{
		MowSpeedMps:      s.Rover.MowSpeedMps,
		GotoSpeedMps:     s.Rover.GotoSpeedMps,
		FixTimeoutSec:    s.Rover.FixTimeoutSec,
		FinishAndRestart: s.Rover.FinishAndRestart,
		AbsolutePosition: s.Rover.AbsolutePosition,
		Lon:              s.Rover.Lon,
		Lat:              s.Rover.Lat,
		BatteryEmptyV:    s.Battery.EmptyV,
		BatteryFullV:     s.Battery.FullV,
		ChargingBelowA:   s.Battery.ChargingBelowA,
		OfflineAfter:     time.Duration(s.Battery.OfflineAfterSec) * time.Second,
	}
}
