package app_test

import (
	"bufio"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

// copyDir copies the files below src into dst.
func copyDir(t *testing.T, src, dst string) {
	t.Helper()
	err := filepath.WalkDir(src, func(path string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return err
		}
		rel, _ := filepath.Rel(src, path)
		b, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		if err := os.MkdirAll(filepath.Join(dst, filepath.Dir(rel)), 0o755); err != nil {
			return err
		}
		return os.WriteFile(filepath.Join(dst, rel), b, 0o600)
	})
	if err != nil {
		t.Fatal(err)
	}
}

func send(t *testing.T, method, url, body string) (int, string) {
	t.Helper()
	req, err := http.NewRequest(method, url, strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, url, err)
	}
	defer func() { _ = res.Body.Close() }()
	b, _ := io.ReadAll(res.Body)
	return res.StatusCode, string(b)
}

func TestFirstStartImportsLegacyData(t *testing.T) {
	cfg := testConfig(t)
	copyDir(t, "testdata/legacy", cfg.DataDir)
	r := startWith(t, cfg)
	waitForRobot(t, r.baseURL, func(robot.StateJSON) bool { return true })

	var view settings.View
	if err := getJSON(r.baseURL+"/api/settings", &view); err != nil {
		t.Fatal(err)
	}
	if view.Settings.Connection.Kind != settings.LinkUART || view.Settings.Rover.MowSpeedMps != 0.4 {
		t.Errorf("settings not imported: %+v", view.Settings)
	}
	var list maps.ListJSON
	if err := getJSON(r.baseURL+"/api/maps", &list); err != nil {
		t.Fatal(err)
	}
	var names []string
	active := ""
	for _, m := range list.Maps {
		names = append(names, m.Name)
		if m.ID == list.ActiveID {
			active = m.Name
		}
	}
	if !slices.Equal(names, []string{"Garden", "Yard"}) || active != "Yard" {
		t.Errorf("maps %v, active %q; want Garden, Yard with Yard active", names, active)
	}
	r.cancel()
	<-r.done

	// The next start keeps changes and does not import again.
	if err := os.WriteFile(filepath.Join(cfg.DataDir, "user", "rovercfg.json"), []byte(`{"mowspeed_setpoint": 0.9}`), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(filepath.Join(cfg.DataDir, "maps", list.Maps[0].ID+".json")); err != nil {
		t.Fatal(err)
	}
	r = startWith(t, cfg)
	if err := getJSON(r.baseURL+"/api/settings", &view); err != nil {
		t.Fatal(err)
	}
	if err := getJSON(r.baseURL+"/api/maps", &list); err != nil {
		t.Fatal(err)
	}
	if view.Settings.Rover.MowSpeedMps != 0.4 || len(list.Maps) != 1 {
		t.Errorf("second start imported again: speed %v, %d maps", view.Settings.Rover.MowSpeedMps, len(list.Maps))
	}
}

func TestStartWithBrokenSettingsFails(t *testing.T) {
	cfg := testConfig(t)
	if err := os.WriteFile(filepath.Join(cfg.DataDir, "settings.json"), []byte("{"), 0o600); err != nil {
		t.Fatal(err)
	}
	r := startWith(t, cfg)
	<-r.done
	if *r.err == nil || !strings.Contains((*r.err).Error(), "settings") {
		t.Errorf("Run err = %v, want a settings error", *r.err)
	}
}

func TestStartWithBrokenMapsFails(t *testing.T) {
	cfg := testConfig(t)
	copyDir(t, "testdata/legacy", cfg.DataDir)
	if err := os.MkdirAll(filepath.Join(cfg.DataDir, "maps"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(cfg.DataDir, "maps", "x.json"), []byte("{"), 0o600); err != nil {
		t.Fatal(err)
	}
	r := startWith(t, cfg)
	<-r.done
	if *r.err == nil || !strings.Contains((*r.err).Error(), "map") {
		t.Errorf("Run err = %v, want a map error", *r.err)
	}
}

func TestChangingTheConnectionReconnects(t *testing.T) {
	simCfg := link.DefaultSimConfig()
	simCfg.Start.X = 42
	remote := testkit.RobotHTTPServer(t, link.NewSim(simCfg))

	r := start(t) // simulator at the demo station
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusIdle && s.Position.X != 42 })

	code, body := send(t, http.MethodPut, r.baseURL+"/api/settings",
		`{"settings": {"connection": {"kind": "http", "httpUrl": "`+remote.URL+`"}}}`)
	if code != http.StatusOK {
		t.Fatalf("PUT settings = %d %s", code, body)
	}
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Online && s.Position.X == 42 })

	// Other settings do not reconnect.
	if code, body := send(t, http.MethodPut, r.baseURL+"/api/settings", `{"settings": {"planner": {"widthM": 0.2}}}`); code != http.StatusOK {
		t.Fatalf("PUT settings = %d %s", code, body)
	}
	if code, _ := send(t, http.MethodPut, r.baseURL+"/api/settings", `{"settings": {"connection": {"kind": "sim"}}}`); code != http.StatusOK {
		t.Fatal("switch back to the simulator failed")
	}
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Online && s.Position.X != 42 })
}

func TestChangedRoverSettingsApplyImmediately(t *testing.T) {
	broker := testkit.StartBroker(t, "127.0.0.1:0")
	commands := broker.Collect(t, "m/command")
	cfg := testConfig(t)
	cfg.Poll.ReconnectDelay = 50 * time.Millisecond
	writeSettings(t, cfg, func(s *settings.Settings) {
		s.Connection.Kind, s.Connection.MQTTBroker, s.Connection.MQTTMower = settings.LinkMQTT, broker.URL(), "m"
	})
	r := startWith(t, cfg)
	waitFor := func(want string) {
		t.Helper()
		deadline := time.Now().Add(3 * time.Second)
		for !slices.Contains(commands(), want) {
			if time.Now().After(deadline) {
				t.Fatalf("command %q not sent; got %q", want, commands())
			}
			time.Sleep(10 * time.Millisecond)
		}
	}
	waitFor(protocol.PositionMode(false, 0, 0)) // sent on connect

	code, body := send(t, http.MethodPut, r.baseURL+"/api/settings",
		`{"settings": {"rover": {"mowSpeedMps": 0.5, "absolutePosition": true, "lon": 13.4, "lat": 52.5}}}`)
	if code != http.StatusOK {
		t.Fatalf("PUT settings = %d %s", code, body)
	}
	waitFor(protocol.PositionMode(true, 13.4, 52.5))

	if code := post(t, r.baseURL+"/api/robot/mow"); code != http.StatusNoContent {
		t.Fatalf("POST mow = %d", code)
	}
	waitFor(protocol.Mow(0.5, 60, false).Encode())
}

func TestUploadAMapToTheSimulator(t *testing.T) {
	r := start(t)
	waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.Status == robot.StatusIdle && s.MapCRC != 0 })

	events := streamEvents(t, r.baseURL, "maps")
	m := `{"name": "Front", "perimeter": [{"x":0,"y":0},{"x":-40.94,"y":0.29},{"x":-40.85,"y":-40.76}],
		"dock": [{"x":-1,"y":3},{"x":1,"y":3}]}`
	code, body := send(t, http.MethodPost, r.baseURL+"/api/maps", m)
	if code != http.StatusCreated {
		t.Fatalf("POST map = %d %s", code, body)
	}
	var created maps.Map
	_ = json.Unmarshal([]byte(body), &created)

	if code, body := send(t, http.MethodPost, r.baseURL+"/api/maps/"+created.ID+"/upload", ""); code != http.StatusNoContent {
		t.Fatalf("upload = %d %s", code, body)
	}
	want := protocol.MapChecksum(created.Robot(nil)).Linux
	s := waitForRobot(t, r.baseURL, func(s robot.StateJSON) bool { return s.MapCRC == want })
	if s.Status != robot.StatusIdle {
		t.Errorf("status after upload = %q", s.Status)
	}
	var robotMap robot.MapJSON
	if err := getJSON(r.baseURL+"/api/robot/map", &robotMap); err != nil || len(robotMap.Perimeter) != 3 || len(robotMap.Way) != 0 {
		t.Errorf("robot map = %+v, %v", robotMap, err)
	}

	deadline := time.After(3 * time.Second)
	for {
		select {
		case data := <-events:
			var list maps.ListJSON
			if err := json.Unmarshal([]byte(data), &list); err != nil {
				t.Fatal(err)
			}
			if list.ActiveID == created.ID {
				return
			}
		case <-deadline:
			t.Fatal("no maps event with the uploaded map active")
		}
	}
}

// streamEvents returns the data of all events of type name.
func streamEvents(t *testing.T, baseURL, name string) <-chan string {
	t.Helper()
	ctx, cancel := context.WithCancel(context.Background())
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, baseURL+"/api/events", nil)
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	out := make(chan string, 100)
	done := make(chan struct{})
	t.Cleanup(func() {
		cancel()
		_ = res.Body.Close()
		<-done
	})
	go func() {
		defer close(done)
		lines := bufio.NewScanner(res.Body)
		event := ""
		for lines.Scan() {
			line := lines.Text()
			if v, ok := strings.CutPrefix(line, "event: "); ok {
				event = v
			} else if v, ok := strings.CutPrefix(line, "data: "); ok && event == name {
				select {
				case out <- v:
				default:
				}
			}
		}
	}()
	return out
}

func TestSettingsEventFollowsChangesWithoutPasswords(t *testing.T) {
	cfg := testConfig(t)
	writeSettings(t, cfg, func(s *settings.Settings) { s.Connection.HTTPPassword = 4711 })
	r := startWith(t, cfg)
	events := streamEvents(t, r.baseURL, "settings")

	next := func() settings.View {
		t.Helper()
		select {
		case data := <-events:
			if strings.Contains(data, "4711") {
				t.Fatalf("settings event leaks the password: %s", data)
			}
			var v settings.View
			if err := json.Unmarshal([]byte(data), &v); err != nil {
				t.Fatal(err)
			}
			return v
		case <-time.After(3 * time.Second):
			t.Fatal("no settings event")
			return settings.View{}
		}
	}
	if v := next(); v.Settings.Appearance.RobotPicture != "default" || !v.Secrets.HTTPPassword {
		t.Fatalf("first event = %+v", v)
	}
	if code, body := send(t, http.MethodPut, r.baseURL+"/api/settings",
		`{"settings": {"appearance": {"robotPicture": "alfred", "robotSizeCm": 130}}}`); code != http.StatusOK {
		t.Fatalf("PUT settings = %d %s", code, body)
	}
	if v := next(); v.Settings.Appearance != (settings.Appearance{RobotPicture: "alfred", RobotSizeCm: 130}) {
		t.Errorf("event after change = %+v", v.Settings.Appearance)
	}
}
