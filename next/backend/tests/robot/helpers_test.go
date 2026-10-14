package robot_test

import (
	"context"
	"errors"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

// fakeSender records payloads and answers like a robot. Behaviour can be
// changed per command name ("AT+C", "AT+W", ...).
type fakeSender struct {
	mu      sync.Mutex
	sent    []string
	fail    map[string]int    // command -> how many times to fail
	replies map[string]string // command -> reply payload override
	block   map[string]bool   // command -> wait until ctx is done
	blocked chan string       // receives the command that started blocking
}

func newFakeSender() *fakeSender {
	return &fakeSender{
		fail:    map[string]int{},
		replies: map[string]string{},
		block:   map[string]bool{},
		blocked: make(chan string, 10),
	}
}

var errLinkDown = errors.New("link down")

func (f *fakeSender) Send(ctx context.Context, payload string) (string, error) {
	name, _, _ := strings.Cut(payload, ",")
	f.mu.Lock()
	f.sent = append(f.sent, payload)
	block := f.block[name]
	failing := f.fail[name] > 0
	if failing {
		f.fail[name]--
	}
	reply, override := f.replies[name]
	f.mu.Unlock()

	if block {
		f.blocked <- name
		<-ctx.Done()
		return "", ctx.Err()
	}
	if failing {
		return "", errLinkDown
	}
	if override {
		return reply, nil
	}
	return defaultReply(payload), nil
}

// defaultReply answers like the firmware: AT+W acks the next index.
func defaultReply(payload string) string {
	name := strings.TrimPrefix(strings.SplitN(payload, ",", 2)[0], "AT+")
	if name == "W" {
		parts := strings.Split(payload, ",")
		start, _ := strconv.Atoi(parts[1])
		return "W," + strconv.Itoa(start+(len(parts)-2)/2)
	}
	if name == "X" {
		return "X,0"
	}
	return name
}

func (f *fakeSender) payloads() []string {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]string(nil), f.sent...)
}

var t0 = time.Date(2026, 6, 1, 12, 0, 0, 0, time.UTC)

type fixture struct {
	robot  *robot.Robot
	sender *fakeSender
	clock  *testkit.FakeClock
}

func newFixture(t *testing.T) fixture {
	t.Helper()
	clock := testkit.NewFakeClock(t0)
	sender := newFakeSender()
	cfg := robot.DefaultConfig()
	cfg.Now = clock.Now
	cfg.Logger = testkit.Logger(t)
	return fixture{robot: robot.New(sender, cfg), sender: sender, clock: clock}
}

// online connects the robot and reports one state.
func (f fixture) online(s protocol.State) {
	f.robot.OnOnline(true)
	f.robot.OnState(s)
}

func state(op protocol.Op) protocol.State {
	return protocol.State{BatteryVoltage: 26, Op: op, Amps: 0.5, Solution: protocol.SolutionFix, MowPointIndex: 7}
}

func pts(coords ...float64) []geo.Point {
	p := make([]geo.Point, len(coords)/2)
	for i := range p {
		p[i] = geo.Point{X: coords[2*i], Y: coords[2*i+1]}
	}
	return p
}
