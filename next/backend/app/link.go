package app

import (
	"context"
	"log/slog"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

// simStateInterval keeps the simulated robot moving smoothly in the browser.
const simStateInterval = 200 * time.Millisecond

// switchSender forwards commands to the current link. The robot keeps it
// while the link changes; without a link the robot is offline.
type switchSender struct {
	mu sync.Mutex
	l  link.Link
}

func (s *switchSender) set(l link.Link) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.l = l
}

func (s *switchSender) Send(ctx context.Context, payload string) (string, error) {
	s.mu.Lock()
	l := s.l
	s.mu.Unlock()
	if l == nil {
		return "", link.ErrOffline
	}
	return l.Send(ctx, payload)
}

// superviseLink runs the link of the current connection settings and
// replaces it when they change (signalled on reconnect), until ctx ends.
//
// simMap is the map a new simulated robot starts with.
func superviseLink(ctx context.Context, cfg Config, store *settings.Store, r *robot.Robot,
	sender *switchSender, reconnect <-chan struct{}, simMap func() protocol.Map,
) {
	log := cfg.Logger.With("feature", "link")
	for {
		conn := store.Get().Connection
		stop := startLink(ctx, cfg, conn, r, sender, log, simMap)
		for changed := false; !changed; {
			select {
			case <-ctx.Done():
				stop()
				return
			case <-reconnect:
				changed = store.Get().Connection != conn
			}
		}
		log.Info("connection settings changed, reconnecting")
		stop()
	}
}

// startLink starts the link for conn and returns a function that stops it,
// waits for its goroutines and releases it.
func startLink(ctx context.Context, cfg Config, conn settings.Connection, r *robot.Robot,
	sender *switchSender, log *slog.Logger, simMap func() protocol.Map,
) (stop func()) {
	m := simMap()
	l, release, sim := newLink(cfg, conn, log, station(m))
	sender.set(l)
	ctx, cancel := context.WithCancel(ctx)
	var wg sync.WaitGroup
	goroutine := func(f func()) {
		wg.Add(1)
		go func() {
			defer wg.Done()
			f()
		}()
	}
	if sim != nil {
		// The map is there before the robot is online: an upload afterwards
		// would clear a route that someone started in the meantime.
		sim.LoadMap(m)
		r.AdoptMap(m)
		goroutine(func() { sim.Run(ctx, cfg.SimTick) })
	}
	goroutine(func() {
		if err := l.Run(ctx, r); err != nil {
			log.Error("robot link stopped", "err", err)
		}
	})
	log.Info("robot link started", "link", conn.Kind)
	return func() {
		cancel()
		wg.Wait()
		sender.set(nil)
		release()
	}
}

// newLink builds the link for conn, a function that releases it and, for
// the simulator, the simulated robot, standing at simStart.
func newLink(cfg Config, conn settings.Connection, log *slog.Logger, simStart geo.Point) (link.Link, func(), *link.Sim) {
	switch conn.Kind {
	case settings.LinkHTTP:
		poll := cfg.Poll
		poll.Encrypt, poll.Password = true, conn.HTTPPassword
		return link.NewPoller(link.NewHTTPTransport(conn.HTTPURL), poll), func() {}, nil
	case settings.LinkUART:
		tr := link.NewUARTTransport(conn.UARTPort, conn.UARTBaud)
		return link.NewPoller(tr, cfg.Poll), func() { _ = tr.Close() }, nil
	case settings.LinkMQTT:
		return link.NewMQTTLink(link.MQTTConfig{
			Broker:         conn.MQTTBroker,
			ClientID:       conn.MQTTClientID,
			Username:       conn.MQTTUser,
			Password:       conn.MQTTPassword,
			MowerName:      conn.MQTTMower,
			ReconnectDelay: cfg.Poll.ReconnectDelay,
			Logger:         log,
		}), func() {}, nil
	}
	simCfg := link.DefaultSimConfig()
	simCfg.Start = simStart
	sim := link.NewSim(simCfg)
	poll := cfg.Poll
	poll.StateInterval = min(poll.StateInterval, simStateInterval) // the simulator is local and cheap
	return link.NewPoller(sim, poll), func() {}, sim
}

// station is where a simulated robot with map m starts: in its docking
// station, or on the perimeter if the map has no dock path.
func station(m protocol.Map) geo.Point {
	if n := len(m.Dock); n > 0 {
		return m.Dock[n-1]
	}
	if len(m.Perimeter) > 0 {
		return m.Perimeter[0]
	}
	return geo.Point{}
}
