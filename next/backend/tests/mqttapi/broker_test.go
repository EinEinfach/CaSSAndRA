package mqttapi_test

import (
	"context"
	"slices"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/mqttapi"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func eventually(t *testing.T, what string, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(5 * time.Second)
	for !cond() {
		if time.Now().After(deadline) {
			t.Fatalf("timed out waiting for %s", what)
		}
		time.Sleep(5 * time.Millisecond)
	}
}

func runAPI(t *testing.T, r *fakeRobot) *testkit.Broker {
	t.Helper()
	b := testkit.StartBroker(t, "127.0.0.1:0")
	api := mqttapi.New(mqttapi.Deps{Robot: r, Tasks: &fakeTasks{robot: r}, Maps: &fakeMaps{}}, mqttapi.Config{Version: "v-test", Logger: testkit.Logger(t)})
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() {
		defer close(done)
		_ = api.Run(ctx, mqttapi.BrokerConfig{
			Broker: b.URL(), ClientID: "api", Prefix: "Garden", Interval: 20 * time.Millisecond,
			ReconnectDelay: 50 * time.Millisecond,
		})
	}()
	t.Cleanup(func() { cancel(); <-done })
	return b
}

func TestTheAPIPublishesAndRunsCommands(t *testing.T) {
	r := &fakeRobot{snap: mowing()}
	b := testkit.StartBroker(t, "127.0.0.1:0")
	robotMsgs := b.Collect(t, "Garden/robot")
	status := b.Collect(t, "Garden/status")
	server := b.Collect(t, "Garden/server")
	api := mqttapi.New(mqttapi.Deps{Robot: r, Tasks: &fakeTasks{robot: r}, Maps: &fakeMaps{}}, mqttapi.Config{Version: "v-test", Logger: testkit.Logger(t)})
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() {
		defer close(done)
		_ = api.Run(ctx, mqttapi.BrokerConfig{Broker: b.URL(), ClientID: "api", Prefix: "Garden", Interval: 20 * time.Millisecond})
	}()
	defer func() { cancel(); <-done }()

	eventually(t, "state topics", func() bool { return len(robotMsgs()) >= 2 && len(server()) > 0 })
	if got := server()[0]; got != `{"software":"CaSSAndRA","version":"v-test","cpuLoad":null,"cpuTemp":null,"memUsage":null,"hddUsage":null}` {
		t.Errorf("server topic = %s", got)
	}

	b.Publish(t, "Garden/api_cmd", `{"robot": {"command": "dock", "value": []}}`)
	eventually(t, "dock", func() bool { return slices.Contains(r.recorded(), "dock") })
	eventually(t, "busy, then ready", func() bool {
		s := status()
		i := slices.Index(s, "busy")
		return i >= 0 && slices.Contains(s[i:], "ready")
	})

	cancel()
	<-done
	eventually(t, "offline", func() bool { return slices.Contains(status(), "offline") })
}

func TestStopDoesNotWaitBehindALongCommand(t *testing.T) {
	r := &fakeRobot{snap: mowing(), block: make(chan struct{})}
	b := runAPI(t, r)
	status := b.Collect(t, "Garden/status")
	eventually(t, "connected", func() bool { return slices.Contains(status(), "ready") })
	time.Sleep(50 * time.Millisecond) // the subscription runs next to the first publications

	b.Publish(t, "Garden/api_cmd", `{"robot": {"command": "mow", "value": ["resume"]}}`)
	time.Sleep(50 * time.Millisecond)
	b.Publish(t, "Garden/api_cmd", `{"robot": {"command": "stop", "value": []}}`)
	eventually(t, "stop", func() bool { return slices.Contains(r.recorded(), "stop") })
	if slices.Contains(r.recorded(), "mow") {
		t.Fatal("mow finished first; the test proves nothing")
	}
	close(r.block)
	eventually(t, "mow", func() bool { return slices.Equal(r.recorded(), []string{"stop", "mow"}) })
}

func TestTheBrokerTellsOfflineWhenTheAPIDisappears(t *testing.T) {
	r := &fakeRobot{snap: mowing()}
	b := runAPI(t, r)
	status := b.Collect(t, "Garden/status")
	eventually(t, "ready", func() bool { return slices.Contains(status(), "ready") })
	if n := b.DropClients("api-"); n != 1 {
		t.Fatalf("dropped %d clients, want the API", n)
	}
	eventually(t, "the last will", func() bool { return slices.Contains(status(), "offline") })
	// The API connects again by itself.
	before := len(status())
	eventually(t, "ready again", func() bool { return slices.Contains(status()[before:], "ready") })
}
