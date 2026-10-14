package link

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// Transport exchanges one framed line with the robot and returns the reply
// line: an HTTP POST, a UART write/read, or the simulator.
type Transport interface {
	Exchange(ctx context.Context, line string) (string, error)
}

// PollConfig controls how often a Poller asks the robot for data.
type PollConfig struct {
	StateInterval     time.Duration
	ObstaclesInterval time.Duration
	StatsInterval     time.Duration
	// ReconnectDelay is the pause after a failed exchange before reconnecting.
	ReconnectDelay time.Duration
	// Encrypt follows the robot's request to encrypt (HTTP). UART must not
	// encrypt: the firmware does not decrypt its console.
	Encrypt  bool
	Password int
}

// DefaultPollConfig matches the legacy CaSSAndRA timing.
func DefaultPollConfig() PollConfig {
	return PollConfig{
		StateInterval:     time.Second,
		ObstaclesInterval: 10 * time.Second,
		StatsInterval:     60 * time.Second,
		ReconnectDelay:    4 * time.Second,
	}
}

// Poller turns a request/reply Transport into a Link by polling state,
// obstacles and stats.
type Poller struct {
	transport Transport
	cfg       PollConfig

	// mu serializes exchanges and guards the connection fields.
	mu     sync.Mutex
	online bool
	key    int // 0 = no encryption
}

// NewPoller returns a Link that polls the robot through t.
func NewPoller(t Transport, cfg PollConfig) *Poller {
	return &Poller{transport: t, cfg: cfg}
}

// Run implements Link.
func (p *Poller) Run(ctx context.Context, h Handler) error {
	for {
		err := p.session(ctx, h)
		if p.setOffline() {
			h.OnOnline(false)
		}
		if ctx.Err() != nil {
			return nil
		}
		if errors.Is(err, errFatal) {
			return err
		}
		select {
		case <-ctx.Done():
			return nil
		case <-time.After(p.cfg.ReconnectDelay):
		}
	}
}

// errFatal marks configuration errors that reconnecting cannot fix.
var errFatal = errors.New("fatal link error")

// session connects and polls until an exchange fails or ctx ends.
func (p *Poller) session(ctx context.Context, h Handler) error {
	if err := p.connect(ctx, h); err != nil {
		return err
	}
	h.OnOnline(true)

	state := time.NewTicker(p.cfg.StateInterval)
	defer state.Stop()
	obstacles := time.NewTicker(p.cfg.ObstaclesInterval)
	defer obstacles.Stop()
	stats := time.NewTicker(p.cfg.StatsInterval)
	defer stats.Stop()

	// Report everything once right after connecting.
	if err := p.poll(ctx, h, protocol.RequestState); err != nil {
		return err
	}
	if err := p.poll(ctx, h, protocol.RequestStats); err != nil {
		return err
	}
	if err := p.poll(ctx, h, protocol.RequestObstacles); err != nil {
		return err
	}
	for {
		var err error
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-state.C:
			err = p.poll(ctx, h, protocol.RequestState)
		case <-obstacles.C:
			err = p.poll(ctx, h, protocol.RequestObstacles)
		case <-stats.C:
			err = p.poll(ctx, h, protocol.RequestStats)
		}
		if err != nil {
			return err
		}
	}
}

func (p *Poller) connect(ctx context.Context, h Handler) error {
	p.mu.Lock()
	defer p.mu.Unlock()
	// AT+V is never encrypted; it tells us whether the rest must be.
	reply, err := p.exchangeLocked(ctx, protocol.RequestVersion, 0)
	if err != nil {
		return err
	}
	v, err := protocol.ParseVersion(reply)
	if err != nil {
		return err
	}
	p.key = 0
	if v.Encrypted && p.cfg.Encrypt {
		key, err := protocol.Key(p.cfg.Password, v.Challenge)
		if err != nil {
			return fmt.Errorf("%w: %w", errFatal, err)
		}
		p.key = key
	}
	p.online = true
	h.OnVersion(v)
	return nil
}

func (p *Poller) poll(ctx context.Context, h Handler, request string) error {
	reply, err := p.Send(ctx, request)
	if err != nil {
		return err
	}
	switch request {
	case protocol.RequestState:
		s, err := protocol.ParseState(reply)
		if err != nil {
			return err
		}
		h.OnState(s)
	case protocol.RequestStats:
		s, err := protocol.ParseStats(reply)
		if err != nil {
			return err
		}
		h.OnStats(s)
	case protocol.RequestObstacles:
		o, err := protocol.ParseObstacles(reply)
		if err != nil {
			return err
		}
		h.OnObstacles(o)
	}
	return nil
}

// Send implements Link.
func (p *Poller) Send(ctx context.Context, payload string) (string, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if !p.online {
		return "", ErrOffline
	}
	return p.exchangeLocked(ctx, payload, p.key)
}

func (p *Poller) exchangeLocked(ctx context.Context, payload string, key int) (string, error) {
	line := protocol.Frame(payload)
	if key != 0 {
		line = protocol.Encrypt(line, key)
	}
	replyLine, err := p.transport.Exchange(ctx, line)
	if err != nil {
		return "", fmt.Errorf("send %s: %w", command(payload), err)
	}
	reply, err := protocol.Unframe(replyLine)
	if err != nil {
		return "", fmt.Errorf("send %s: %w", command(payload), err)
	}
	if !protocol.ReplyMatches(payload, reply) {
		return "", fmt.Errorf("send %s: %w: unexpected reply %q", command(payload), protocol.ErrMalformed, reply)
	}
	return reply, nil
}

// setOffline marks the link offline and reports whether it was online.
func (p *Poller) setOffline() bool {
	p.mu.Lock()
	defer p.mu.Unlock()
	was := p.online
	p.online = false
	return was
}

// command shortens a payload for error messages ("AT+W,0,1,2,..." -> "AT+W").
func command(payload string) string {
	for i := 0; i < len(payload); i++ {
		if payload[i] == ',' {
			return payload[:i]
		}
	}
	return payload
}
