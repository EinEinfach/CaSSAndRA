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

// Link kinds.
const (
	LinkSim  = "sim"
	LinkHTTP = "http"
	LinkUART = "uart"
	LinkMQTT = "mqtt"
)

// LinkConfig selects and configures the connection to the robot.
type LinkConfig struct {
	Kind string // LinkSim, LinkHTTP, LinkUART or LinkMQTT
	// HTTP: robot URL and the password from the firmware's config.h (0 = none).
	HTTPURL      string
	HTTPPassword int
	// UART: serial port and baud rate.
	UARTPort string
	UARTBaud int
	MQTT     link.MQTTConfig
}

func (c LinkConfig) validate() error {
	switch c.Kind {
	case LinkSim:
	case LinkHTTP:
		if c.HTTPURL == "" {
			return errors.New("invalid config: the http link needs a robot URL")
		}
	case LinkUART:
		if c.UARTPort == "" || c.UARTBaud <= 0 {
			return errors.New("invalid config: the uart link needs a port and a baud rate")
		}
	case LinkMQTT:
		if c.MQTT.Broker == "" || c.MQTT.MowerName == "" {
			return errors.New("invalid config: the mqtt link needs a broker and a mower name")
		}
	default:
		return fmt.Errorf("invalid config: unknown link %q (sim, http, uart or mqtt)", c.Kind)
	}
	return nil
}

// Config holds everything the app needs to start.
type Config struct {
	Version string
	UI      fs.FS
	Logger  *slog.Logger
	Robot   robot.Config
	Link    LinkConfig
	// SimTick is the simulation step of the simulated robot.
	SimTick time.Duration
	// Poll controls how often the robot is asked for data.
	Poll link.PollConfig
	// PublishInterval is how often the browser gets state updates (if changed).
	PublishInterval time.Duration
	// Heartbeat keeps idle event streams open through proxies.
	Heartbeat time.Duration
}

// DefaultConfig returns the legacy defaults with the simulated robot.
func DefaultConfig() Config {
	return Config{
		Robot:           robot.DefaultConfig(),
		Link:            LinkConfig{Kind: LinkSim, UARTBaud: 115200},
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
		"Heartbeat": c.Heartbeat, "Robot.OfflineAfter": c.Robot.OfflineAfter,
	} {
		if d <= 0 {
			return fmt.Errorf("invalid config: %s must be positive, got %v (start from DefaultConfig)", name, d)
		}
	}
	return c.Link.validate()
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

	// Deferred in reverse: cancel the background goroutines, wait for them,
	// and only then release the link they use.
	l, closeLink := newLink(cfg)
	defer closeLink()
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

	r := robot.New(l, cfg.Robot)
	hub := server.NewHub(cfg.Heartbeat)

	if sim, ok := l.(*simLink); ok {
		goroutine(func() { sim.sim.Run(ctx, cfg.SimTick) })
		goroutine(func() { uploadDemoMap(ctx, r, log) })
	}
	goroutine(func() {
		if err := l.Run(ctx, r); err != nil {
			log.Error("robot link stopped", "err", err)
		}
	})
	goroutine(func() { r.PublishState(ctx, cfg.PublishInterval, func(b []byte) { hub.Publish("robot", b) }) })

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
	log.Info("CaSSAndRA started", "addr", ln.Addr().String(), "version", cfg.Version, "link", cfg.Link.Kind)

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

// simLink is the simulated robot behind a poller; the app also steps the
// simulation and gives it the demo garden.
type simLink struct {
	*link.Poller
	sim *link.Sim
}

// newLink builds the configured link and a function that releases it.
func newLink(cfg Config) (link.Link, func()) {
	lc := cfg.Link
	switch lc.Kind {
	case LinkHTTP:
		poll := cfg.Poll
		poll.Encrypt, poll.Password = true, lc.HTTPPassword
		return link.NewPoller(link.NewHTTPTransport(lc.HTTPURL), poll), func() {}
	case LinkUART:
		tr := link.NewUARTTransport(lc.UARTPort, lc.UARTBaud)
		return link.NewPoller(tr, cfg.Poll), func() { _ = tr.Close() }
	case LinkMQTT:
		mc := lc.MQTT
		mc.Logger = cfg.Logger.With("feature", "link")
		return link.NewMQTTLink(mc), func() {}
	}
	simCfg := link.DefaultSimConfig()
	simCfg.Start = link.DemoStation
	sim := link.NewSim(simCfg)
	return &simLink{Poller: link.NewPoller(sim, cfg.Poll), sim: sim}, func() {}
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
