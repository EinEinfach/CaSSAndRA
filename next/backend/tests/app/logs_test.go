package app_test

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/logs"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/system"
)

// The log view: a typed command goes to the simulator, and it, its reply and
// what the features log show up in GET /api/logs.
func TestRawCommandAndLogView(t *testing.T) {
	r := start(t)
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusIdle })

	code, body := send(t, http.MethodPost, r.baseURL+"/api/robot/raw", `{"line":"AT+V"}`)
	var raw robot.RawJSON
	if err := json.Unmarshal([]byte(body), &raw); err != nil || code != http.StatusOK || !strings.HasPrefix(raw.Reply, "V,") {
		t.Fatalf("POST raw = %d %s (%v)", code, body, err)
	}

	var list logs.ListJSON
	if err := getJSON(r.baseURL+"/api/logs", &list); err != nil {
		t.Fatal(err)
	}
	var all []string
	for _, e := range list.Entries {
		all = append(all, e.Message)
	}
	text := strings.Join(all, "\n")
	for _, want := range []string{"cmd=raw line=AT+V", "raw command reply"} {
		if !strings.Contains(text, want) {
			t.Errorf("log view lacks %q:\n%s", want, text)
		}
	}
	last := list.Entries[len(list.Entries)-1].Seq
	if err := getJSON(r.baseURL+"/api/logs?after="+strconv.FormatInt(last, 10), &list); err != nil {
		t.Fatal(err)
	}
	for _, e := range list.Entries {
		if e.Seq <= last {
			t.Errorf("after=%d returned seq %d", last, e.Seq)
		}
	}

	var info system.InfoJSON
	if err := getJSON(r.baseURL+"/api/system", &info); err != nil {
		t.Errorf("GET /api/system: %v", err)
	}
}
