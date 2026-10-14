package testkit

import (
	"io"
	"log/slog"
	"net"
	"sync"
	"testing"

	mochi "github.com/mochi-mqtt/server/v2"
	"github.com/mochi-mqtt/server/v2/hooks/auth"
	"github.com/mochi-mqtt/server/v2/listeners"
	"github.com/mochi-mqtt/server/v2/packets"
)

// Broker is an in-process MQTT broker for tests.
type Broker struct {
	Addr     string // host:port
	server   *mochi.Server
	stopOnce sync.Once
}

// StartBroker listens on addr ("127.0.0.1:0" for a free port) until the test ends.
func StartBroker(t testing.TB, addr string) *Broker {
	t.Helper()
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	srv := mochi.New(&mochi.Options{InlineClient: true, Logger: slog.New(slog.NewTextHandler(io.Discard, nil))})
	if err := srv.AddHook(new(auth.AllowHook), nil); err != nil {
		t.Fatal(err)
	}
	if err := srv.AddListener(listeners.NewNet("test", ln)); err != nil {
		t.Fatal(err)
	}
	go func() { _ = srv.Serve() }()
	b := &Broker{Addr: ln.Addr().String(), server: srv}
	t.Cleanup(b.Stop)
	return b
}

// URL returns the broker address for MQTT clients.
func (b *Broker) URL() string { return "tcp://" + b.Addr }

// Stop closes the broker; calling it again does nothing.
func (b *Broker) Stop() { b.stopOnce.Do(func() { _ = b.server.Close() }) }

// Publish sends payload on topic like a client would.
func (b *Broker) Publish(t testing.TB, topic, payload string) {
	t.Helper()
	if err := b.server.Publish(topic, []byte(payload), false, 0); err != nil {
		t.Fatalf("publish %s: %v", topic, err)
	}
}

// Collect records every payload published on topic and returns a function
// that reports them so far.
func (b *Broker) Collect(t testing.TB, topic string) func() []string {
	t.Helper()
	var mu sync.Mutex
	var got []string
	err := b.server.Subscribe(topic, 1, func(_ *mochi.Client, _ packets.Subscription, pk packets.Packet) {
		mu.Lock()
		got = append(got, string(pk.Payload))
		mu.Unlock()
	})
	if err != nil {
		t.Fatal(err)
	}
	return func() []string {
		mu.Lock()
		defer mu.Unlock()
		return append([]string(nil), got...)
	}
}
