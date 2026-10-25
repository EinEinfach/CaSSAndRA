package app_test

import (
	"encoding/json"
	"net/http"
	"strings"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/schedule"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func TestTheScheduleMowsAndSendsTheRobotHome(t *testing.T) {
	cfg := testConfig(t)
	cfg.Planner = &testkit.FakePlanner{}
	// Monday 26 October 2026, shortly before the window.
	clock := testkit.NewFakeClock(time.Date(2026, 10, 26, 8, 59, 0, 0, time.Local))
	cfg.Schedule = schedule.Config{Now: clock.Now, Interval: 10 * time.Millisecond}
	r := startWith(t, cfg)
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusIdle && s.MapCRC != 0 })
	events := streamEvents(t, r.baseURL, "schedule")

	code, body := send(t, http.MethodPost, r.baseURL+"/api/maps", `{"name": "Back",
		"perimeter": [{"x":0,"y":0},{"x":8,"y":0},{"x":8,"y":8},{"x":0,"y":8}],
		"dock": [{"x":1,"y":3},{"x":-1,"y":3}]}`)
	if code != http.StatusCreated {
		t.Fatalf("POST map = %d %s", code, body)
	}
	var m maps.Map
	_ = json.Unmarshal([]byte(body), &m)
	if code, body := send(t, http.MethodPut, r.baseURL+"/api/maps/active", `{"id":"`+m.ID+`"}`); code != http.StatusNoContent {
		t.Fatalf("activate = %d %s", code, body)
	}
	code, body = send(t, http.MethodPost, r.baseURL+"/api/tasks", `{"name":"All","mapId":"`+m.ID+`",
		"parts":[{"parameters":{"pattern":"lines","widthM":0.18,"angleDeg":0,"distanceToBorder":1,"mowArea":true,"borderLaps":1,"mowExclusions":false,"borderCcw":false}}]}`)
	if code != http.StatusCreated {
		t.Fatalf("POST task = %d %s", code, body)
	}
	var task tasks.Task
	_ = json.Unmarshal([]byte(body), &task)
	code, body = send(t, http.MethodPut, r.baseURL+"/api/schedule", `{"schedule":{"active":true,"days":[`+
		`{"start":"09:00","end":"12:00","taskIds":["`+task.ID+`"]}`+
		strings.Repeat(`,{"start":"12:00","end":"12:00","taskIds":[]}`, 6)+`]}}`)
	if code != http.StatusOK {
		t.Fatalf("PUT schedule = %d %s", code, body)
	}

	state := func(want schedule.State) {
		t.Helper()
		deadline := time.After(5 * time.Second)
		for {
			select {
			case data := <-events:
				var s schedule.JSON
				if err := json.Unmarshal([]byte(data), &s); err != nil {
					t.Fatal(err)
				}
				if s.Status.State == want {
					return
				}
			case <-deadline:
				t.Fatalf("no schedule event with state %q", want)
			}
		}
	}
	state(schedule.StateWaiting)
	clock.Advance(time.Minute)
	state(schedule.StateStarted)
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusMow })

	clock.Advance(3 * time.Hour)
	state(schedule.StateDone)
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool {
		return s.Status == robot.StatusDocking && s.DockReason == robot.DockReasonSchedule
	})
}
