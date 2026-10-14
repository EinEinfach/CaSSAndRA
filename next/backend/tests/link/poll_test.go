package link_test

import (
	"context"
	"errors"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// recorder is a link.Handler that remembers what it was told.
type recorder struct {
	mu        sync.Mutex
	online    []bool
	versions  []protocol.Version
	states    []protocol.State
	stats     int
	obstacles int
}

func (r *recorder) OnOnline(o bool) { r.mu.Lock(); r.online = append(r.online, o); r.mu.Unlock() }
func (r *recorder) OnVersion(v protocol.Version) {
	r.mu.Lock()
	r.versions = append(r.versions, v)
	r.mu.Unlock()
}
func (r *recorder) OnState(s protocol.State) {
	r.mu.Lock()
	r.states = append(r.states, s)
	r.mu.Unlock()
}
func (r *recorder) OnStats(protocol.Stats)    { r.mu.Lock(); r.stats++; r.mu.Unlock() }
func (r *recorder) OnObstacles([][]geo.Point) { r.mu.Lock(); r.obstacles++; r.mu.Unlock() }

func (r *recorder) waitFor(t *testing.T, what string, cond func(r *recorder) bool) {
	t.Helper()
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		r.mu.Lock()
		ok := cond(r)
		r.mu.Unlock()
		if ok {
			return
		}
		time.Sleep(5 * time.Millisecond)
	}
	t.Fatalf("timed out waiting for %s", what)
}

func fastPoll() link.PollConfig {
	return link.PollConfig{
		StateInterval:     10 * time.Millisecond,
		ObstaclesInterval: 30 * time.Millisecond,
		StatsInterval:     50 * time.Millisecond,
		ReconnectDelay:    20 * time.Millisecond,
	}
}

// run starts p in the background and stops it at the end of the test.
func run(t *testing.T, p *link.Poller, h link.Handler) {
	t.Helper()
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- p.Run(ctx, h) }()
	t.Cleanup(func() {
		cancel()
		select {
		case err := <-done:
			if err != nil {
				t.Errorf("Run returned %v after cancel, want nil", err)
			}
		case <-time.After(2 * time.Second):
			t.Error("Run did not return after cancel")
		}
	})
}

func TestPollerReportsEverything(t *testing.T) {
	s := newSim(t)
	p := link.NewPoller(s, fastPoll())
	rec := &recorder{}
	run(t, p, rec)

	rec.waitFor(t, "online, version, states, stats and obstacles", func(r *recorder) bool {
		return len(r.online) > 0 && r.online[0] && len(r.versions) == 1 &&
			len(r.states) >= 3 && r.stats >= 2 && r.obstacles >= 2
	})
	rec.mu.Lock()
	defer rec.mu.Unlock()
	if rec.versions[0].Firmware != "Sunray" {
		t.Errorf("version = %+v", rec.versions[0])
	}
	if st := rec.states[0]; st.Y != -2 || st.Op != protocol.OpIdle {
		t.Errorf("first state = %+v", st)
	}
}

func TestPollerSendDeliversCommands(t *testing.T) {
	s := newSim(t)
	p := link.NewPoller(s, fastPoll())

	if _, err := p.Send(context.Background(), protocol.RequestState); !errors.Is(err, link.ErrOffline) {
		t.Fatalf("Send before Run err = %v, want ErrOffline", err)
	}

	rec := &recorder{}
	run(t, p, rec)
	rec.waitFor(t, "online", func(r *recorder) bool { return len(r.online) > 0 })

	for _, msg := range protocol.MapUpload(garden) {
		if _, err := p.Send(context.Background(), msg); err != nil {
			t.Fatalf("Send(%q): %v", msg, err)
		}
	}
	reply, err := p.Send(context.Background(), protocol.Mow(0.3, 60, false).Encode())
	if err != nil || reply != "C" {
		t.Fatalf("Send mow = %q, %v; want C", reply, err)
	}
	if op := s.State().Op; op != protocol.OpMow {
		t.Errorf("simulator op = %v, want mow", op)
	}
	rec.waitFor(t, "a mowing state", func(r *recorder) bool {
		return len(r.states) > 0 && r.states[len(r.states)-1].Op == protocol.OpMow
	})
}

func TestPollerEncryptsWhenTheRobotAsks(t *testing.T) {
	cfg := link.DefaultSimConfig()
	cfg.Password = 1234
	s := link.NewSim(cfg)
	pc := fastPoll()
	pc.Encrypt, pc.Password = true, 1234
	p := link.NewPoller(s, pc)
	rec := &recorder{}
	run(t, p, rec)

	rec.waitFor(t, "states over an encrypted link", func(r *recorder) bool { return len(r.states) >= 2 })
	if _, err := p.Send(context.Background(), protocol.Stop().Encode()); err != nil {
		t.Errorf("encrypted Send: %v", err)
	}
}

func TestPollerFailsOnUnusablePassword(t *testing.T) {
	cfg := link.DefaultSimConfig()
	cfg.Password = 1234 // challenge 199
	pc := fastPoll()
	pc.Encrypt, pc.Password = true, 199*3 // key 0

	err := link.NewPoller(link.NewSim(cfg), pc).Run(context.Background(), &recorder{})
	if !errors.Is(err, protocol.ErrMalformed) {
		t.Errorf("Run err = %v, want an encryption key error", err)
	}
}

func TestPollerReconnects(t *testing.T) {
	s := newSim(t)
	p := link.NewPoller(s, fastPoll())
	rec := &recorder{}
	run(t, p, rec)
	rec.waitFor(t, "online", func(r *recorder) bool { return len(r.online) == 1 })

	s.SetOffline(true)
	rec.waitFor(t, "offline", func(r *recorder) bool { return len(r.online) == 2 })
	if _, err := p.Send(context.Background(), protocol.Stop().Encode()); !errors.Is(err, link.ErrOffline) {
		t.Errorf("Send while offline err = %v, want ErrOffline", err)
	}
	time.Sleep(100 * time.Millisecond) // several failed reconnects

	s.SetOffline(false)
	rec.waitFor(t, "online again", func(r *recorder) bool { return len(r.online) == 3 })
	rec.mu.Lock()
	defer rec.mu.Unlock()
	if want := []bool{true, false, true}; !equalBools(rec.online, want) {
		t.Errorf("online reports = %v, want %v (no repeats while reconnecting)", rec.online, want)
	}
	if len(rec.versions) != 2 {
		t.Errorf("got %d version reports, want one per connection", len(rec.versions))
	}
}

// scripted is a Transport that answers with fixed reply payloads.
type scripted struct {
	mu      sync.Mutex
	replies map[string]string // request command -> reply payload
	sent    []string
}

func (s *scripted) Exchange(_ context.Context, line string) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	payload, err := protocol.Unframe(line)
	if err != nil {
		return "", err
	}
	s.sent = append(s.sent, payload)
	name, _, _ := strings.Cut(payload, ",")
	reply, ok := s.replies[name]
	if !ok {
		return "", link.ErrNoReply
	}
	return protocol.Frame(reply) + "\r\n", nil
}

func TestPollerRejectsMismatchedReply(t *testing.T) {
	tr := &scripted{replies: map[string]string{
		"AT+V":  "V,Sunray,1.0.332,0,0",
		"AT+S":  "S,27.5,1,2,1.5,2,0,0,0.65,0,0,0,0.02,28,0.1,0,0",
		"AT+T":  "T," + strings.Repeat("0,", 23) + "0",
		"AT+S2": "S2,0",
		"AT+C":  "M", // wrong answer
	}}
	p := link.NewPoller(tr, fastPoll())
	rec := &recorder{}
	run(t, p, rec)
	rec.waitFor(t, "online", func(r *recorder) bool { return len(r.online) > 0 })

	_, err := p.Send(context.Background(), protocol.Stop().Encode())
	if !errors.Is(err, protocol.ErrMalformed) || !strings.Contains(err.Error(), "AT+C") {
		t.Errorf("err = %v, want ErrMalformed mentioning AT+C", err)
	}
}

func TestPollerReconnectsAfterMalformedPollReply(t *testing.T) {
	good := map[string]string{
		"AT+V":  "V,Sunray,1.0.332,0,0",
		"AT+S":  "S,27.5,1,2,1.5,2,0,0,0.65,0,0,0,0.02,28,0.1,0,0",
		"AT+T":  "T," + strings.Repeat("0,", 23) + "0",
		"AT+S2": "S2,0",
	}
	tests := []struct{ request, reply string }{
		{"AT+V", "V,Sunray"},
		{"AT+S", "S,1,2"},
		{"AT+T", "T,1,2"},
		{"AT+S2", "S2,x"},
		{"AT+S", "C"}, // answer to a different request
	}
	for _, tt := range tests {
		t.Run(tt.request+" "+tt.reply, func(t *testing.T) {
			replies := map[string]string{}
			for k, v := range good {
				replies[k] = v
			}
			replies[tt.request] = tt.reply
			tr := &scripted{replies: replies}
			p := link.NewPoller(tr, fastPoll())
			rec := &recorder{}
			run(t, p, rec)

			rec.waitFor(t, "several connection attempts", func(*recorder) bool {
				tr.mu.Lock()
				defer tr.mu.Unlock()
				n := 0
				for _, s := range tr.sent {
					if s == "AT+V" {
						n++
					}
				}
				return n >= 3
			})
			rec.mu.Lock()
			defer rec.mu.Unlock()
			for i := 1; i < len(rec.online); i++ {
				if rec.online[i] == rec.online[i-1] {
					t.Errorf("online reports repeat: %v", rec.online)
				}
			}
		})
	}
}

func TestDefaultPollConfigMatchesLegacy(t *testing.T) {
	c := link.DefaultPollConfig()
	if c.StateInterval != time.Second || c.ObstaclesInterval != 10*time.Second ||
		c.StatsInterval != time.Minute || c.ReconnectDelay != 4*time.Second || c.Encrypt {
		t.Errorf("DefaultPollConfig() = %+v", c)
	}
}

func equalBools(a, b []bool) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
