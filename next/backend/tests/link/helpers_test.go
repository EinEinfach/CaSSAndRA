package link_test

import (
	"context"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// send frames payload, lets the simulator answer and returns the reply payload.
func send(t *testing.T, s *link.Sim, payload string) string {
	t.Helper()
	line, err := s.Exchange(context.Background(), protocol.Frame(payload)+"\n")
	if err != nil {
		t.Fatalf("Exchange(%q): %v", payload, err)
	}
	reply, err := protocol.Unframe(line)
	if err != nil {
		t.Fatalf("reply to %q: %v", payload, err)
	}
	return reply
}

func pts(coords ...float64) []geo.Point {
	p := make([]geo.Point, len(coords)/2)
	for i := range p {
		p[i] = geo.Point{X: coords[2*i], Y: coords[2*i+1]}
	}
	return p
}

// garden is a 10x10 m lawn with a dock path ending at the station (0,-2)
// and a mow route along three sides.
var garden = protocol.Map{
	Perimeter:  pts(0, 0, 10, 0, 10, 10, 0, 10),
	Exclusions: [][]geo.Point{pts(4, 4, 5, 4, 5, 5)},
	Dock:       pts(0, 1, 0, -2),
	Way:        pts(1, 1, 9, 1, 9, 9, 1, 9),
}

func upload(t *testing.T, s *link.Sim, m protocol.Map) {
	t.Helper()
	for _, msg := range protocol.MapUpload(m) {
		send(t, s, msg)
	}
}

func newSim(t *testing.T) *link.Sim {
	t.Helper()
	cfg := link.DefaultSimConfig()
	cfg.Start = geo.Point{X: 0, Y: -2}
	return link.NewSim(cfg)
}

// stepUntil advances the simulation in 100 ms steps until done reports true.
func stepUntil(t *testing.T, s *link.Sim, limit time.Duration, done func(protocol.State) bool) protocol.State {
	t.Helper()
	for elapsed := time.Duration(0); elapsed < limit; elapsed += 100 * time.Millisecond {
		if st := s.State(); done(st) {
			return st
		}
		s.Step(100 * time.Millisecond)
	}
	st := s.State()
	if !done(st) {
		t.Fatalf("condition not reached within %v simulated time; state %+v", limit, st)
	}
	return st
}
