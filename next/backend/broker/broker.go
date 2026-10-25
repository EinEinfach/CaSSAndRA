// Package broker is an MQTT broker built into CaSSAndRA, for users without
// one of their own: the native app and the robot's MQTT bridge connect to
// it, and so does the MQTT API. Only one user, with a password, may connect.
package broker

import (
	"crypto/subtle"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"strconv"
	"sync"
	"sync/atomic"
	"time"

	mochi "github.com/mochi-mqtt/server/v2"
	"github.com/mochi-mqtt/server/v2/listeners"
	"github.com/mochi-mqtt/server/v2/packets"
)

// MinPasswordLen keeps the broker from running with a trivial password:
// everyone in the network who gets in can drive the mower.
const MinPasswordLen = 8

// closeTimeout bounds mochi's Close, which can deadlock (see Close).
const closeTimeout = 2 * time.Second

// Config is the broker to run.
type Config struct {
	Enabled  bool
	Port     int
	User     string
	Password string
}

func (c Config) validate() error {
	switch {
	case c.Port < 1 || c.Port > 65535:
		return fmt.Errorf("port %d is not between 1 and 65535", c.Port)
	case c.User == "":
		return errors.New("a user is needed")
	case len(c.Password) < MinPasswordLen:
		return fmt.Errorf("the password needs at least %d characters", MinPasswordLen)
	}
	return nil
}

// Status tells whether the broker runs.
type Status struct {
	Enabled bool   `json:"enabled"`
	Running bool   `json:"running"`
	Port    int    `json:"port"`
	Clients int    `json:"clients"` // connected now, CaSSAndRA's own API included
	Error   string `json:"error"`   // why it does not run, e.g. the port is taken
}

// Service runs the broker as configured and restarts it when the
// configuration changes. Safe for concurrent use.
type Service struct {
	log *slog.Logger

	mu      sync.Mutex
	cfg     Config
	running *running
	err     error
}

type running struct {
	srv  *mochi.Server
	ln   net.Listener
	auth *authHook
}

// New returns a stopped broker; Apply starts it.
func New(log *slog.Logger) *Service {
	if log == nil {
		log = slog.New(slog.DiscardHandler)
	}
	return &Service{log: log}
}

// Apply runs the broker with cfg: it starts, stops or restarts it as needed.
// It returns why the broker cannot run; Status keeps that reason too.
func (s *Service) Apply(cfg Config) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if cfg == s.cfg && (s.running != nil || !cfg.Enabled) {
		return nil // unchanged; a failed start is tried again
	}
	s.stopLocked()
	s.cfg, s.err = cfg, nil
	if !cfg.Enabled {
		return nil
	}
	if err := cfg.validate(); err != nil {
		s.err = fmt.Errorf("broker: %w", err)
		return s.err
	}
	r, err := start(cfg, s.log)
	if err != nil {
		s.err = err
		s.log.Error("mqtt broker not started", "err", err)
		return err
	}
	s.running = r
	s.log.Info("mqtt broker started", "port", cfg.Port)
	return nil
}

// Close stops the broker.
func (s *Service) Close() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.stopLocked()
}

// Status tells whether the broker runs and how many clients are connected.
func (s *Service) Status() Status {
	s.mu.Lock()
	defer s.mu.Unlock()
	st := Status{Enabled: s.cfg.Enabled, Port: s.cfg.Port, Running: s.running != nil}
	if s.running != nil {
		st.Clients = int(atomic.LoadInt64(&s.running.srv.Info.ClientsConnected))
	}
	if s.err != nil {
		st.Error = s.err.Error()
	}
	return st
}

// Handler serves GET /api/broker (Status).
func (s *Service) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/broker", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(s.Status()) // the client is gone if this fails
	})
	return mux
}

func start(cfg Config, log *slog.Logger) (*running, error) {
	ln, err := net.Listen("tcp", net.JoinHostPort("", strconv.Itoa(cfg.Port)))
	if err != nil {
		return nil, fmt.Errorf("broker: port %d: %w (is another MQTT broker running?)", cfg.Port, err)
	}
	srv := mochi.New(&mochi.Options{Logger: log.With("feature", "broker")})
	auth := &authHook{user: cfg.User, password: cfg.Password, log: log}
	if err := srv.AddHook(auth, nil); err != nil {
		_ = ln.Close()
		return nil, fmt.Errorf("broker: %w", err)
	}
	if err := srv.AddListener(listeners.NewNet("cassandra", ln)); err != nil {
		_ = ln.Close()
		return nil, fmt.Errorf("broker: %w", err)
	}
	go func() {
		if err := srv.Serve(); err != nil {
			log.Error("mqtt broker", "err", err)
		}
	}()
	return &running{srv: srv, ln: ln, auth: auth}, nil
}

// stopLocked closes the running broker. mochi v2.7.9 can deadlock in Close
// (a read lock taken twice while a client is removed), so the port is freed
// first and Close gets a deadline; a stuck broker is left behind.
func (s *Service) stopLocked() {
	if s.running == nil {
		return
	}
	r := s.running
	s.running = nil
	_ = r.ln.Close()
	done := make(chan struct{})
	go func() {
		_ = r.srv.Close()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(closeTimeout):
		s.log.Warn("mqtt broker did not close in time")
	}
}

// authHook lets only the configured user in, and that user everywhere.
type authHook struct {
	mochi.HookBase
	user, password string
	log            *slog.Logger
}

func (h *authHook) ID() string { return "cassandra-auth" }

func (h *authHook) Provides(b byte) bool {
	return b == mochi.OnConnectAuthenticate || b == mochi.OnACLCheck
}

func (h *authHook) OnConnectAuthenticate(cl *mochi.Client, pk packets.Packet) bool {
	userOK := subtle.ConstantTimeCompare(pk.Connect.Username, []byte(h.user)) == 1
	passOK := subtle.ConstantTimeCompare(pk.Connect.Password, []byte(h.password)) == 1
	if !userOK || !passOK {
		h.log.Warn("mqtt broker: login refused", "client", cl.ID, "remote", cl.Net.Remote)
		return false
	}
	return true
}

func (h *authHook) OnACLCheck(*mochi.Client, string, bool) bool { return true }
