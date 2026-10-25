package app_test

import (
	"fmt"
	"net"
	"strings"
	"testing"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"

	"github.com/EinEinfach/CaSSAndRA/next/backend/broker"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

// Like a user without a broker of their own: the native app connects to the
// one built into CaSSAndRA.
func TestTheNativeAppOnTheBuiltInBroker(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	port := ln.Addr().(*net.TCPAddr).Port
	_ = ln.Close()

	cfg := testConfig(t)
	writeSettings(t, cfg, func(s *settings.Settings) {
		s.Broker = settings.Broker{Enabled: true, Port: port, User: "cassandra", Password: "mow-the-lawn"}
		s.API = settings.API{Enabled: true, UseBuiltinBroker: true, ServerName: "Garden", ClientID: "api"}
	})
	r := startWith(t, cfg)
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusIdle && s.MapCRC != 0 })

	robotMsgs := make(chan string, 16)
	app := mqtt.NewClient(mqtt.NewClientOptions().
		AddBroker(fmt.Sprintf("tcp://127.0.0.1:%d", port)).SetClientID("native-app").
		SetUsername("cassandra").SetPassword("mow-the-lawn").
		SetConnectRetry(true).SetConnectRetryInterval(50 * time.Millisecond))
	if tok := app.Connect(); !tok.WaitTimeout(5*time.Second) || tok.Error() != nil {
		t.Fatalf("connect: %v", tok.Error())
	}
	defer app.Disconnect(50)
	app.Subscribe("Garden/robot", 0, func(_ mqtt.Client, m mqtt.Message) {
		select {
		case robotMsgs <- string(m.Payload()):
		default:
		}
	}).WaitTimeout(2 * time.Second)

	select {
	case m := <-robotMsgs:
		if !strings.Contains(m, `"status":"idle"`) {
			t.Errorf("robot topic = %s", m)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("no robot topic from the API through the built-in broker")
	}

	var st broker.Status
	if err := getJSON(r.baseURL+"/api/broker", &st); err != nil || !st.Running || st.Clients < 2 {
		t.Errorf("broker status = %+v (%v), want running with the API and the app", st, err)
	}

	app.Publish("Garden/api_cmd", 0, false, `{"robot": {"command": "dock", "value": []}}`)
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool {
		return s.Status == robot.StatusDocking || s.Status == robot.StatusCharging
	})

	// Without the password nobody gets in.
	stranger := mqtt.NewClient(mqtt.NewClientOptions().
		AddBroker(fmt.Sprintf("tcp://127.0.0.1:%d", port)).SetClientID("stranger").SetConnectTimeout(2 * time.Second))
	if tok := stranger.Connect(); tok.WaitTimeout(3*time.Second) && tok.Error() == nil {
		stranger.Disconnect(50)
		t.Error("a client without password got in")
	}
}
