package app_test

import (
	"encoding/json"
	"net/http"
	"slices"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/mqttapi"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func TestTheMQTTAPIDrivesTheSimulator(t *testing.T) {
	b := testkit.StartBroker(t, "127.0.0.1:0")
	robotTopic := b.Collect(t, "Garden/robot")
	cfg := testConfig(t)
	writeSettings(t, cfg, func(s *settings.Settings) {
		s.API = settings.API{Enabled: true, Broker: b.URL(), ServerName: "Garden", ClientID: "api"}
	})
	r := startWith(t, cfg)
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusIdle && s.MapCRC != 0 })

	last := func() mqttapi.RobotJSON {
		var got mqttapi.RobotJSON
		if msgs := robotTopic(); len(msgs) > 0 {
			_ = json.Unmarshal([]byte(msgs[len(msgs)-1]), &got)
		}
		return got
	}
	deadline := time.Now().Add(10 * time.Second)
	for last().Status != "idle" {
		if time.Now().After(deadline) {
			t.Fatalf("no idle robot on Garden/robot: %v", robotTopic())
		}
		time.Sleep(20 * time.Millisecond)
	}
	b.Publish(t, "Garden/api_cmd", `{"robot": {"command": "mow", "value": ["resume"]}}`)
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusMow })
	b.Publish(t, "Garden/api_cmd", `{"robot": {"command": "stop", "value": []}}`)
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusIdle })

	// Switched off in the settings, the API says goodbye.
	status := b.Collect(t, "Garden/status")
	if code, body := send(t, http.MethodPut, r.baseURL+"/api/settings", `{"settings":{"api":{"enabled":false}}}`); code != http.StatusOK {
		t.Fatalf("PUT settings = %d %s", code, body)
	}
	deadline = time.Now().Add(5 * time.Second)
	for !slices.Contains(status(), "offline") {
		if time.Now().After(deadline) {
			t.Fatalf("no offline after switching the API off: %v", status())
		}
		time.Sleep(20 * time.Millisecond)
	}
}
