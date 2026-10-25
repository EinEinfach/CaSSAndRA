package mqttapi_test

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"os"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/mqttapi"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

func golden(t *testing.T, name string) []string {
	t.Helper()
	b, err := os.ReadFile("testdata/" + name)
	if err != nil {
		t.Fatal(err)
	}
	return strings.Split(strings.TrimSpace(string(b)), "\n")
}

func handle(t *testing.T, api *mqttapi.API, cmd string) []mqttapi.Message {
	t.Helper()
	msgs, err := api.Handle(context.Background(), []byte(cmd))
	if err != nil {
		t.Fatalf("%s: %v", cmd, err)
	}
	return msgs
}

func payloads(msgs []mqttapi.Message, topic string) []string {
	var out []string
	for _, m := range msgs {
		if m.Topic == topic {
			out = append(out, string(m.Payload))
		}
	}
	return out
}

// A plan of the whole garden, computed a minute after t0.
func gardenPlan() *tasks.Plan {
	return &tasks.Plan{
		MapID: "g1", MapUpdatedAt: t0, Parts: []tasks.Part{{Parameters: defaults}},
		Route:     []geo.Point{{X: 1, Y: -1.5}, {X: 2.5, Y: 1}, {X: 9, Y: 1}},
		CreatedAt: t0.Add(time.Minute),
	}
}

func TestCoordsAreLikeLegacy(t *testing.T) {
	api, _, ft, _ := newAPI(t)
	ft.plan = gardenPlan()
	got := payloads(handle(t, api, `{"coords": {"command": "update", "value": ["preview", "currentMap"]}}`), "coords")
	want := append(golden(t, "coords_current_map.json"), golden(t, "coords_preview.json")...)
	if !slices.Equal(got, want) {
		t.Errorf("coords\n got %s\nwant %s", strings.Join(got, "\n"), strings.Join(want, "\n"))
	}
}

func TestCoordsWithoutAnything(t *testing.T) {
	api, _, _, fm := newAPI(t)
	fm.active = ""
	got := payloads(handle(t, api, `{"coords": {"command": "update", "value": ["currentMap", "obstacles", "preview", "mowPath"]}}`), "coords")
	want := golden(t, "coords_empty.json")
	// legacy order: currentMap, preview, mowPath, obstacles
	want = []string{want[3], want[0], want[1], want[2]}
	if !slices.Equal(got, want) {
		t.Errorf("coords\n got %s\nwant %s", strings.Join(got, "\n"), strings.Join(want, "\n"))
	}
}

func TestCoordsOfRouteAndObstacles(t *testing.T) {
	api, r, _, _ := newAPI(t)
	r.route = protocol.Map{Way: []geo.Point{{X: 1, Y: 1}, {X: 2, Y: 1}}}
	r.set(func(s *robot.Snapshot) { s.Obstacles = [][]geo.Point{{{X: 4, Y: 4}, {X: 4.5, Y: 4}, {X: 4.5, Y: 4.5}}} })
	got := payloads(handle(t, api, `{"coords": {"command": "update", "value": ["mowPath", "obstacles"]}}`), "coords")
	if len(got) != 2 ||
		!strings.Contains(got[0], `"geometry":{"type":"LineString","coordinates":[[[1.0,1.0],[2.0,1.0]]]}`) ||
		!strings.Contains(got[1], `{"name":"obstacle"},"geometry":{"type":"Polygon","coordinates":[[[4.0,4.0],[4.5,4.0],[4.5,4.5]]]}`) {
		t.Errorf("coords = %s", strings.Join(got, "\n"))
	}
	var ids mqttapi.MapJSON
	_ = json.Unmarshal(topic(t, api.State(), "map"), &ids)
	for _, id := range []struct{ name, id, in string }{{"mow path", ids.MowPathID, got[0]}, {"obstacles", ids.ObstaclesID, got[1]}} {
		if id.id == "" || !strings.Contains(id.in, `"id":"`+id.id+`"`) {
			t.Errorf("%s id %q is not the one of its coordinates", id.name, id.id)
		}
	}
}

func TestMapTopic(t *testing.T) {
	api, r, ft, _ := newAPI(t)
	ft.plan = gardenPlan()
	r.route = protocol.Map{Way: []geo.Point{{X: 0, Y: 0}, {X: 10, Y: 0}, {X: 10, Y: 10}, {X: 0, Y: 10}}}
	r.set(func(s *robot.Snapshot) { s.MowPointIndex = 2 })
	got := topic(t, api.State(), "map")
	want := `{"mapId":"g1-1793005200000","previewId":"g1-1793005260000000000","mowPathId":"` +
		mustID(t, api) + `","obstaclesId":"","mowprogressIdxPercent":50,"mowprogressDistancePercent":33,` +
		`"finishedDistance":10,"distanceTotal":30,"finishedIdx":2,"idxTotal":4,"areaTotal":80}`
	if string(got) != want {
		t.Errorf("map topic\n got %s\nwant %s", got, want)
	}
}

func mustID(t *testing.T, api *mqttapi.API) string {
	t.Helper()
	var m mqttapi.MapJSON
	if err := json.Unmarshal(topic(t, api.State(), "map"), &m); err != nil || m.MowPathID == "" {
		t.Fatalf("no mow path id: %v", err)
	}
	return m.MowPathID
}

func TestTheMapIdFollowsChanges(t *testing.T) {
	api, _, _, fm := newAPI(t)
	id := func() string {
		var m mqttapi.MapJSON
		_ = json.Unmarshal(topic(t, api.State(), "map"), &m)
		return m.MapID
	}
	before := id()
	g := fm.maps["g1"]
	g.UpdatedAt = g.UpdatedAt.Add(time.Second)
	fm.maps["g1"] = g
	if id() == before {
		t.Error("an edited map keeps its id; the app would not load it again")
	}
}

func TestMowParameters(t *testing.T) {
	api, _, _, _ := newAPI(t)
	if got := string(topic(t, api.State(), "mowParameters")); got !=
		`{"mowPattern":"lines","width":0.18,"angle":0,"distanceToBorder":1,"mowArea":true,"borderLaps":1,"mowExclusionBorder":false,"mowBorderCcw":false}` {
		t.Errorf("mowParameters = %s", got)
	}
	// Values outside the legacy ranges are ignored, the others taken.
	handle(t, api, `{"map": {"command": "setMowParameters", "value": {"mowPattern": "spiral", "width": 0.25,
		"angle": 400, "distanceToBorder": 2, "mowArea": false, "borderLaps": 9, "mowExclusionBorder": true, "mowBorderCcw": true}}}`)
	if got := string(topic(t, api.State(), "mowParameters")); got !=
		`{"mowPattern":"lines","width":0.25,"angle":0,"distanceToBorder":2,"mowArea":false,"borderLaps":1,"mowExclusionBorder":true,"mowBorderCcw":true}` {
		t.Errorf("after setMowParameters = %s", got)
	}
}

func TestMowAllAndSelectionUseTheAPIParameters(t *testing.T) {
	api, r, ft, _ := newAPI(t)
	handle(t, api, `{"map": {"command": "setMowParameters", "value": {"mowPattern": "rings", "width": 0.2, "angle": 30,
		"distanceToBorder": 0, "mowArea": true, "borderLaps": 2, "mowExclusionBorder": false, "mowBorderCcw": false}}}`)
	handle(t, api, `{"robot": {"command": "mow", "value": ["all"]}}`)
	handle(t, api, `{"map": {"command": "setSelection", "value": {"x": [1, 4, 4, 1], "y": [1, 1, 4, 4]}}}`)
	handle(t, api, `{"robot": {"command": "mow", "value": ["selection"]}}`)

	want := tasks.Parameters{Pattern: "rings", WidthM: 0.2, AngleDeg: 30, MowArea: true, BorderLaps: 2}
	if len(ft.requests) != 2 {
		t.Fatalf("requests = %+v", ft.requests)
	}
	all, sel := ft.requests[0], ft.requests[1]
	if len(all.Parts) != 1 || all.Parts[0].Parameters != want || len(all.Parts[0].Selection) != 0 {
		t.Errorf("mow all = %+v", all)
	}
	if len(sel.Parts) != 1 || sel.Parts[0].Parameters != want || len(sel.Parts[0].Selection) != 4 || sel.Parts[0].Selection[2] != (geo.Point{X: 4, Y: 4}) {
		t.Errorf("mow selection = %+v", sel)
	}
	if got := r.recorded(); !slices.Equal(got, []string{"plan and start", "plan and start"}) {
		t.Errorf("calls = %v", got)
	}
}

func TestMowWithoutSelectionOrTasksSendsNothing(t *testing.T) {
	for _, what := range []string{"selection", "task"} {
		api, r, _, _ := newAPI(t)
		_, err := api.Handle(context.Background(), []byte(`{"robot": {"command": "mow", "value": ["`+what+`"]}}`))
		if !errors.Is(err, mqttapi.ErrInvalid) || len(r.recorded()) != 0 {
			t.Errorf("mow %s: err %v, calls %v", what, err, r.recorded())
		}
	}
}

func TestResetRouteAndObstacles(t *testing.T) {
	api, r, ft, _ := newAPI(t)
	ft.plan = gardenPlan()
	handle(t, api, `{"map": {"command": "resetRoute", "value": []}}`)
	handle(t, api, `{"map": {"command": "resetObstacles", "value": []}}`)
	if ft.plan != nil || !slices.Equal(r.recorded(), []string{"clear plan", "clear obstacles"}) {
		t.Errorf("plan %v, calls %v", ft.plan, r.recorded())
	}
	if _, err := api.Handle(context.Background(), []byte(`{"coords": {"command": "update", "value": ["everything"]}}`)); !errors.Is(err, mqttapi.ErrInvalid) {
		t.Errorf("unknown coords: %v", err)
	}
	if !bytes.Contains(topic(t, api.State(), "map"), []byte(`"previewId":""`)) {
		t.Error("the preview id stays after resetRoute")
	}
}
