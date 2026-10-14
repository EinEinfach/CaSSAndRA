package link_test

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func newMQTTLink(b *testkit.Broker) *link.MQTTLink {
	return link.NewMQTTLink(link.MQTTConfig{
		Broker:         b.URL(),
		ClientID:       "cassandra-test",
		MowerName:      "garden/alfred",
		ReconnectDelay: 50 * time.Millisecond,
	})
}

// runLink runs l until the test ends and checks it stops cleanly.
func runLink(t *testing.T, l link.Link, h link.Handler) {
	t.Helper()
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- l.Run(ctx, h) }()
	t.Cleanup(func() {
		cancel()
		select {
		case err := <-done:
			if err != nil {
				t.Errorf("Run = %v", err)
			}
		case <-time.After(3 * time.Second):
			t.Error("Run did not stop")
		}
	})
}

func lastOnline(r *recorder) (bool, bool) {
	if len(r.online) == 0 {
		return false, false
	}
	return r.online[len(r.online)-1], true
}

func TestMQTTLinkReceivesBridgeMessages(t *testing.T) {
	b := testkit.StartBroker(t, "127.0.0.1:0")
	rec := &recorder{}
	runLink(t, newMQTTLink(b), rec)
	rec.waitFor(t, "online", func(r *recorder) bool { o, ok := lastOnline(r); return ok && o })

	b.Publish(t, "garden/alfred/props", `{"firmware":"Sunray","version":"1.0.332"}`)
	b.Publish(t, "garden/alfred/state", `{"battery_voltage":27.5,"position":{"x":1,"y":2,"solution":2},"job":1}`)
	b.Publish(t, "garden/alfred/stats", `{"duration_mow":42}`)
	b.Publish(t, "garden/alfred/other", `ignored`)

	rec.waitFor(t, "version, state and stats", func(r *recorder) bool {
		return len(r.versions) == 1 && len(r.states) == 1 && r.stats == 1
	})
	rec.mu.Lock()
	defer rec.mu.Unlock()
	if s := rec.states[0]; s.X != 1 || s.Y != 2 || s.Op != protocol.OpMow || s.BatteryVoltage != 27.5 {
		t.Errorf("state = %+v", s)
	}
	if rec.versions[0].Version != "1.0.332" {
		t.Errorf("version = %+v", rec.versions[0])
	}
}

func TestMQTTLinkFollowsTheRobotOnlineTopic(t *testing.T) {
	b := testkit.StartBroker(t, "127.0.0.1:0")
	rec := &recorder{}
	runLink(t, newMQTTLink(b), rec)
	rec.waitFor(t, "online", func(r *recorder) bool { return len(r.online) == 1 })

	b.Publish(t, "garden/alfred/online", "false")
	rec.waitFor(t, "robot offline", func(r *recorder) bool { return len(r.online) == 2 })
	b.Publish(t, "garden/alfred/online", "false") // no repeat
	b.Publish(t, "garden/alfred/online", "nonsense")
	b.Publish(t, "garden/alfred/online", "true")
	rec.waitFor(t, "robot online again", func(r *recorder) bool { return len(r.online) == 3 })

	rec.mu.Lock()
	defer rec.mu.Unlock()
	if !equalBools(rec.online, []bool{true, false, true}) {
		t.Errorf("online = %v", rec.online)
	}
}

func TestMQTTLinkIgnoresBrokenMessages(t *testing.T) {
	b := testkit.StartBroker(t, "127.0.0.1:0")
	rec := &recorder{}
	runLink(t, newMQTTLink(b), rec)
	rec.waitFor(t, "online", func(r *recorder) bool { return len(r.online) == 1 })

	b.Publish(t, "garden/alfred/state", `{"broken`)
	b.Publish(t, "garden/alfred/stats", `[]`)
	b.Publish(t, "garden/alfred/props", `nope`)
	b.Publish(t, "garden/alfred/state", `{"battery_voltage":26,"position":{"x":0,"y":0},"job":0}`)
	rec.waitFor(t, "the valid state", func(r *recorder) bool { return len(r.states) == 1 })
	rec.mu.Lock()
	defer rec.mu.Unlock()
	if rec.stats != 0 || len(rec.versions) != 0 {
		t.Errorf("broken messages were reported: %d stats, %d versions", rec.stats, len(rec.versions))
	}
}

func TestMQTTLinkSendsCommands(t *testing.T) {
	b := testkit.StartBroker(t, "127.0.0.1:0")
	sent := b.Collect(t, "garden/alfred/command")
	l := newMQTTLink(b)

	if _, err := l.Send(context.Background(), "AT+C"); !errors.Is(err, link.ErrOffline) {
		t.Fatalf("Send before Run err = %v, want ErrOffline", err)
	}

	rec := &recorder{}
	runLink(t, l, rec)
	rec.waitFor(t, "online", func(r *recorder) bool { return len(r.online) == 1 })

	reply, err := l.Send(context.Background(), protocol.Dock().Encode())
	if err != nil || reply != "" {
		t.Fatalf("Send = %q, %v; want no reply", reply, err)
	}
	deadline := time.Now().Add(2 * time.Second)
	for len(sent()) == 0 && time.Now().Before(deadline) {
		time.Sleep(5 * time.Millisecond)
	}
	if got := sent(); len(got) != 1 || got[0] != "AT+C,0,4,-1,-1,-1,-1,-1,-1,-1,-1,-1" {
		t.Errorf("published %q, want the raw dock command like legacy", got)
	}

	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := l.Send(ctx, "AT+C"); !errors.Is(err, context.Canceled) {
		t.Errorf("Send with cancelled context err = %v", err)
	}
}

func TestMQTTLinkReconnectsAfterBrokerRestart(t *testing.T) {
	b := testkit.StartBroker(t, "127.0.0.1:0")
	addr := b.Addr
	l := newMQTTLink(b)
	rec := &recorder{}
	runLink(t, l, rec)
	rec.waitFor(t, "online", func(r *recorder) bool { return len(r.online) == 1 })

	b.Stop()
	rec.waitFor(t, "offline", func(r *recorder) bool { return len(r.online) == 2 })
	if _, err := l.Send(context.Background(), "AT+C"); !errors.Is(err, link.ErrOffline) {
		t.Errorf("Send while broker is down err = %v, want ErrOffline", err)
	}

	b2 := testkit.StartBroker(t, addr)
	rec.waitFor(t, "online again", func(r *recorder) bool { return len(r.online) == 3 })
	b2.Publish(t, "garden/alfred/state", `{"battery_voltage":26,"position":{"x":0,"y":0},"job":0}`)
	rec.waitFor(t, "state after reconnect (subscriptions renewed)", func(r *recorder) bool { return len(r.states) == 1 })
}
