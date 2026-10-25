package broker_test

import (
	"errors"
	"fmt"
	"net"
	"strings"
	"testing"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"

	"github.com/EinEinfach/CaSSAndRA/next/backend/broker"
)

func freePort(t *testing.T) int {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = ln.Close() }()
	return ln.Addr().(*net.TCPAddr).Port
}

func connect(t *testing.T, port int, user, password string) (mqtt.Client, error) {
	t.Helper()
	c := mqtt.NewClient(mqtt.NewClientOptions().
		AddBroker(fmt.Sprintf("tcp://127.0.0.1:%d", port)).
		SetClientID(fmt.Sprintf("test-%d", time.Now().UnixNano())).
		SetUsername(user).SetPassword(password).
		SetConnectTimeout(2 * time.Second))
	tok := c.Connect()
	if !tok.WaitTimeout(3 * time.Second) {
		return nil, errors.New("connect: timeout")
	}
	if err := tok.Error(); err != nil {
		return nil, fmt.Errorf("connect: %w", err)
	}
	t.Cleanup(func() { c.Disconnect(50) })
	return c, nil
}

func running(t *testing.T) (*broker.Service, int) {
	t.Helper()
	s := broker.New(nil)
	port := freePort(t)
	if err := s.Apply(broker.Config{Enabled: true, Port: port, User: "cassandra", Password: "mow-the-lawn"}); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(s.Close)
	return s, port
}

func TestTheUserCanPublishAndSubscribe(t *testing.T) {
	s, port := running(t)
	app, err := connect(t, port, "cassandra", "mow-the-lawn")
	if err != nil {
		t.Fatal(err)
	}
	got := make(chan string, 1)
	if tok := app.Subscribe("Garden/robot", 0, func(_ mqtt.Client, m mqtt.Message) { got <- string(m.Payload()) }); !tok.WaitTimeout(2*time.Second) || tok.Error() != nil {
		t.Fatal(tok.Error())
	}
	api, err := connect(t, port, "cassandra", "mow-the-lawn")
	if err != nil {
		t.Fatal(err)
	}
	api.Publish("Garden/robot", 0, false, `{"status":"idle"}`).WaitTimeout(time.Second)
	select {
	case m := <-got:
		if m != `{"status":"idle"}` {
			t.Errorf("got %s", m)
		}
	case <-time.After(3 * time.Second):
		t.Fatal("no message")
	}
	if st := s.Status(); !st.Running || st.Clients != 2 || st.Port != port || st.Error != "" {
		t.Errorf("status = %+v", st)
	}
}

func TestStrangersStayOut(t *testing.T) {
	_, port := running(t)
	for _, c := range []struct{ user, pass string }{{"cassandra", "wrong-password"}, {"", ""}, {"admin", "mow-the-lawn"}} {
		if _, err := connect(t, port, c.user, c.pass); err == nil {
			t.Errorf("%q/%q got in", c.user, c.pass)
		}
	}
}

func TestTheBrokerNeedsAPassword(t *testing.T) {
	for _, cfg := range []broker.Config{
		{Enabled: true, Port: 1883, User: "cassandra", Password: "short"},
		{Enabled: true, Port: 1883, User: "", Password: "long-enough"},
		{Enabled: true, Port: 0, User: "cassandra", Password: "long-enough"},
	} {
		s := broker.New(nil)
		if err := s.Apply(cfg); err == nil {
			s.Close()
			t.Errorf("%+v started", cfg)
		}
		if st := s.Status(); st.Running || st.Error == "" {
			t.Errorf("status = %+v, want not running with a reason", st)
		}
	}
}

func TestATakenPortIsReported(t *testing.T) {
	ln, err := net.Listen("tcp", ":0")
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = ln.Close() }()
	port := ln.Addr().(*net.TCPAddr).Port
	s := broker.New(nil)
	defer s.Close()
	cfg := broker.Config{Enabled: true, Port: port, User: "cassandra", Password: "mow-the-lawn"}
	if err := s.Apply(cfg); err == nil || !strings.Contains(s.Status().Error, "another MQTT broker") {
		t.Fatalf("err = %v, status %+v", err, s.Status())
	}
	_ = ln.Close()
	// The same settings again: the start is tried again.
	if err := s.Apply(cfg); err != nil || !s.Status().Running {
		t.Errorf("after the port was freed: %v, %+v", err, s.Status())
	}
}

func TestSwitchingOffFreesThePort(t *testing.T) {
	s, port := running(t)
	if err := s.Apply(broker.Config{Port: port}); err != nil {
		t.Fatal(err)
	}
	if st := s.Status(); st.Running || st.Enabled {
		t.Errorf("status = %+v", st)
	}
	ln, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		t.Fatalf("port still taken: %v", err)
	}
	_ = ln.Close()
}
