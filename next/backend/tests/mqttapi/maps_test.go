package mqttapi_test

import (
	"context"
	"errors"
	"slices"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

func TestMapsTopicAndSelect(t *testing.T) {
	f := newFixture(t)
	if got := string(topic(t, f.api.State(), "maps")); got != `{"loaded":"Garden","available":["Garden"]}` {
		t.Errorf("maps = %s", got)
	}
	got := payloads(handle(t, f.api, `{"maps": {"command": "select", "value": ["Garden"]}}`), "mapsCoords")
	// legacy maps_to_geojson: stored points, rings open, no naming feature
	want := `{"type":"FeatureCollection","features":[` +
		`{"type":"Feature","properties":{"name":"perimeter"},"geometry":{"type":"Polygon","coordinates":[[[0.0,0.0],[10.0,0.0],[10.0,8.0],[0.0,8.0]]]}},` +
		`{"type":"Feature","properties":{"name":"dockpoints"},"geometry":{"type":"LineString","coordinates":[[1.0,1.0],[1.0,-1.5]]}},` +
		`{"type":"Feature","properties":{"name":"search wire"},"geometry":{"type":"LineString","coordinates":[[5.0,0.0],[5.0,4.0]]}},` +
		`{"type":"Feature","properties":{"name":"exclusion"},"idx":0,"geometry":{"type":"Polygon","coordinates":[[[2.0,2.0],[3.0,2.0],[3.0,3.0]]]}}]}`
	if len(got) != 1 || got[0] != want {
		t.Errorf("mapsCoords\n got %v\nwant %s", got, want)
	}
	if got := payloads(handle(t, f.api, `{"maps": {"command": "select", "value": []}}`), "mapsCoords"); !slices.Equal(got, []string{"{}"}) {
		t.Errorf("select nothing = %v", got)
	}
}

// The app's map editor sends rings and lines as flat lists.
const savedMap = `{"maps": {"command": "save", "value": {"type": "FeatureCollection", "features": [
	{"type": "Feature", "properties": {"name": "Back", "oldName": "Garden"}},
	{"type": "Feature", "properties": {"name": "perimeter"}, "geometry": {"type": "Polygon", "coordinates": [[0, 0], [6, 0], [6, 5], [0, 5], [0, 0]]}},
	{"type": "Feature", "properties": {"name": "exclusion"}, "geometry": {"type": "Polygon", "coordinates": [[1, 1], [2, 1], [2, 2]]}},
	{"type": "Feature", "properties": {"name": "dockPath"}, "geometry": {"type": "LineString", "coordinates": [[1, 0.5], [1, -1]]}},
	{"type": "Feature", "properties": {"name": "searchWire"}, "geometry": {"type": "LineString", "coordinates": [[3, 0], [3, 2]]}}]}}}`

func TestMapsSaveCreatesANewMapWithTheTasksOfTheOldOne(t *testing.T) {
	f := newFixture(t)
	f.addTask(t, "Front")
	handle(t, f.api, savedMap)
	back, err := mapNamed(f, "Back")
	if err != nil {
		t.Fatal(err)
	}
	want := maps.Map{
		ID: back.ID, Name: "Back",
		Perimeter:  []geo.Point{{X: 0, Y: 0}, {X: 6, Y: 0}, {X: 6, Y: 5}, {X: 0, Y: 5}},
		Exclusions: [][]geo.Point{{{X: 1, Y: 1}, {X: 2, Y: 1}, {X: 2, Y: 2}}},
		Dock:       []geo.Point{{X: 1, Y: 0.5}, {X: 1, Y: -1}},
		SearchWire: []geo.Point{{X: 3, Y: 0}, {X: 3, Y: 2}},
	}
	if !mapsEqual(back, want) {
		t.Errorf("saved map = %+v", back)
	}
	var copied []string
	for _, tk := range f.saved.List() {
		if tk.MapID == back.ID {
			copied = append(copied, tk.Name)
		}
	}
	if !slices.Equal(copied, []string{"Front"}) {
		t.Errorf("tasks of the new map = %v, want Front copied", copied)
	}
	// Like legacy, a taken name is refused.
	if _, err := f.api.Handle(context.Background(), []byte(savedMap)); !errors.Is(err, maps.ErrNameTaken) {
		t.Errorf("save again: %v", err)
	}
}

func mapNamed(f *fixture, name string) (maps.Map, error) {
	for _, m := range f.maps.List() {
		if m.Name == name {
			return m, nil
		}
	}
	return maps.Map{}, maps.ErrNotFound
}

func mapsEqual(a, b maps.Map) bool {
	return a.ID == b.ID && a.Name == b.Name && slices.Equal(a.Perimeter, b.Perimeter) &&
		slices.EqualFunc(a.Exclusions, b.Exclusions, slices.Equal) && slices.Equal(a.Dock, b.Dock) &&
		slices.Equal(a.SearchWire, b.SearchWire)
}

func TestMapsLoadRenameCopyRemove(t *testing.T) {
	f := newFixture(t)
	handle(t, f.api, savedMap)
	back, _ := mapNamed(f, "Back")

	handle(t, f.api, `{"maps": {"command": "load", "value": ["Back"]}}`)
	if f.maps.active != back.ID || !slices.Equal(f.robot.recorded(), []string{"upload 4 points, way 0"}) {
		t.Errorf("load: active %q, calls %v", f.maps.active, f.robot.recorded())
	}
	handle(t, f.api, `{"maps": {"command": "rename", "value": ["Back", "Backyard"]}}`)
	handle(t, f.api, `{"maps": {"command": "copy", "value": ["Backyard"]}}`)
	handle(t, f.api, `{"maps": {"command": "remove", "value": ["Garden"]}}`)
	var names []string
	for _, m := range f.maps.List() {
		names = append(names, m.Name)
	}
	slices.Sort(names)
	if !slices.Equal(names, []string{"Backyard", "Backyard_copy"}) {
		t.Errorf("maps = %v", names)
	}
	if _, err := f.api.Handle(context.Background(), []byte(`{"maps": {"command": "load", "value": ["Nowhere"]}}`)); !errors.Is(err, maps.ErrNotFound) {
		t.Errorf("load unknown: %v", err)
	}
}

func TestTasksTopicAndSelect(t *testing.T) {
	f := newFixture(t)
	f.addTask(t, "Front", tasks.Part{
		Selection:  []geo.Point{{X: 1, Y: 1}, {X: 4, Y: 1}, {X: 4, Y: 4}},
		Parameters: tasks.Parameters{Pattern: "rings", WidthM: 0.2, AngleDeg: 45, MowArea: true, BorderLaps: 2},
	}, tasks.Part{Parameters: defaults})
	f.addTask(t, "Back")
	if got := string(topic(t, f.api.State(), "tasks")); got != `{"selected":[],"loaded":[],"available":["Back","Front"]}` {
		t.Errorf("tasks = %s", got)
	}
	got := payloads(handle(t, f.api, `{"tasks": {"command": "select", "value": ["Front", "Unknown"]}}`), "coords")
	want := `{"type":"FeatureCollection","features":[` +
		`{"type":"Feature","properties":{"id":"Front","mapName":"Garden","name":"task"}},` +
		`{"type":"Feature","properties":{"name":0},"geometry":{"type":"LineString","coordinates":[[[1.0,1.0],[4.0,1.0],[4.0,4.0]]]}},` +
		`{"type":"Feature","properties":{"angle":45,"borderLaps":2,"distanceToBorder":0,"mowArea":true,"mowBorderCcw":false,"mowExclusionBorder":false,"mowPattern":"rings","name":0,"type":"lasso","width":0.2},` +
		`"geometry":{"type":"Polygon","coordinates":[[[1.0,1.0],[4.0,1.0],[4.0,4.0],[1.0,1.0]]]}},` +
		`{"type":"Feature","properties":{"name":1},"geometry":{"type":"LineString","coordinates":[[[1.0,1.0],[9.0,1.0]]]}},` +
		`{"type":"Feature","properties":{"angle":0,"borderLaps":1,"distanceToBorder":1,"mowArea":true,"mowBorderCcw":false,"mowExclusionBorder":false,"mowPattern":"lines","name":1,"type":"map","width":0.18},` +
		`"geometry":{"type":"Polygon","coordinates":[[[0.0,0.0],[10.0,0.0],[10.0,8.0],[0.0,8.0]]]}}]}`
	if len(got) != 1 || got[0] != want {
		t.Errorf("task coords\n got %v\nwant %s", got, want)
	}
	if got := string(topic(t, f.api.State(), "tasks")); got != `{"selected":["Front"],"loaded":[],"available":["Back","Front"]}` {
		t.Errorf("tasks after select = %s", got)
	}
	// mow task starts the selection
	handle(t, f.api, `{"robot": {"command": "mow", "value": ["task"]}}`)
	front, _ := taskNamed(f, "Front")
	if len(f.tasks.requests) != 1 || !slices.Equal(f.tasks.requests[0].TaskIDs, []string{front.ID}) {
		t.Errorf("mow task requests = %+v", f.tasks.requests)
	}
}

func taskNamed(f *fixture, name string) (tasks.Task, error) {
	for _, tk := range f.saved.List() {
		if tk.Name == name {
			return tk, nil
		}
	}
	return tasks.Task{}, tasks.ErrNotFound
}

func TestTasksLoadSendsTheRouteWithoutMowing(t *testing.T) {
	f := newFixture(t)
	f.addTask(t, "Front")
	f.addTask(t, "Back")
	handle(t, f.api, `{"tasks": {"command": "load", "value": ["Back", "Front"]}}`)
	back, _ := taskNamed(f, "Back")
	front, _ := taskNamed(f, "Front")
	if len(f.tasks.requests) != 1 || !slices.Equal(f.tasks.requests[0].TaskIDs, []string{back.ID, front.ID}) {
		t.Errorf("requests = %+v, want Back then Front", f.tasks.requests)
	}
	if got := f.robot.recorded(); !slices.Equal(got, []string{"preview", "upload 4 points, way 3"}) {
		t.Errorf("calls = %v, want a preview and an upload, no mow", got)
	}
	if got := string(topic(t, f.api.State(), "tasks")); !strings.Contains(got, `"loaded":["Back","Front"]`) {
		t.Errorf("tasks = %s", got)
	}
}

// The task editor of the app: a part with selection and its preview route.
const savedTask = `{"tasks": {"command": "save", "value": {"type": "FeatureCollection", "features": [
	{"type": "Feature", "properties": {"taskName": "Edges"}},
	{"type": "Feature", "properties": {"subtaskNr": 0, "mowParameters": {"mowPattern": "squares", "width": 0.2,
		"angle": 90, "distanceToBorder": 0, "mowArea": true, "borderLaps": 1, "mowExclusionBorder": false, "mowBorderCcw": true}},
	 "geometry": [{"type": "Polygon", "coordinates": [[[1.0, 1.0], [3.0, 1.0], [3.0, 3.0], [1.0, 1.0]]]},
	              {"type": "LineString", "coordinates": [[[1.0, 1.0], [3.0, 1.0]]]}]},
	[{"type": "Polygon", "coordinates": []}, {"type": "LineString", "coordinates": [[]]}]]}}}`

func TestTasksSave(t *testing.T) {
	f := newFixture(t)
	handle(t, f.api, savedTask)
	edges, err := taskNamed(f, "Edges")
	if err != nil {
		t.Fatal(err)
	}
	want := tasks.Part{
		Selection:  []geo.Point{{X: 1, Y: 1}, {X: 3, Y: 1}, {X: 3, Y: 3}},
		Parameters: tasks.Parameters{Pattern: "squares", WidthM: 0.2, AngleDeg: 90, MowArea: true, BorderLaps: 1, BorderCCW: true},
	}
	if edges.MapID != "g1" || len(edges.Parts) != 1 || !slices.Equal(edges.Parts[0].Selection, want.Selection) || edges.Parts[0].Parameters != want.Parameters {
		t.Errorf("saved task = %+v", edges)
	}
	if _, err := f.api.Handle(context.Background(), []byte(savedTask)); !errors.Is(err, tasks.ErrNameTaken) {
		t.Errorf("save again: %v", err)
	}
}

func TestTasksCalculateEchoesTheRequestWithTheRoute(t *testing.T) {
	f := newFixture(t)
	got := payloads(handle(t, f.api, `{"tasks": {"command": "calculate", "value": {"type": "FeatureCollection", "features": [
		{"type": "Feature", "properties": {"taskName": "", "mowParameters": {"mowPattern": "lines", "width": 0.18, "angle": 0, "distanceToBorder": 1, "mowArea": true, "borderLaps": 1, "mowExclusionBorder": false, "mowBorderCcw": false}}},
		{"type": "Feature", "properties": {"subtaskNr": 2, "mowParameters": {"mowPattern": "lines", "width": 0.18, "angle": 0, "distanceToBorder": 1, "mowArea": true, "borderLaps": 1, "mowExclusionBorder": false, "mowBorderCcw": false}},
		 "geometry": {"type": "Polygon", "coordinates": [[[1.0, 1.0], [3.0, 1.0], [3.0, 3.0], [1.0, 1.0]]]}}]}}}`), "coords")
	want := `{"features":[{"properties":{"mowParameters":{"angle":0,"borderLaps":1,"distanceToBorder":1,"mowArea":true,"mowBorderCcw":false,"mowExclusionBorder":false,"mowPattern":"lines","width":0.18},"name":"taskPreview","taskName":""},"type":"Feature"},` +
		`{"geometry":{"type":"LineString","coordinates":[[[1.0,1.0],[3.0,1.0],[3.0,3.0]]]},"properties":{"mowParameters":{"angle":0,"borderLaps":1,"distanceToBorder":1,"mowArea":true,"mowBorderCcw":false,"mowExclusionBorder":false,"mowPattern":"lines","width":0.18},"subtaskNr":2},"type":"Feature"}],"type":"FeatureCollection"}`
	if len(got) != 1 || got[0] != want {
		t.Errorf("calculate\n got %v\nwant %s", got, want)
	}
	if f.tasks.plan != nil {
		t.Error("calculate changed the preview of the browsers")
	}
}

func TestTasksRenameCopyRemove(t *testing.T) {
	f := newFixture(t)
	f.addTask(t, "Front")
	f.addTask(t, "Back")
	handle(t, f.api, `{"tasks": {"command": "rename", "value": ["Front", "Lawn"]}}`)
	handle(t, f.api, `{"tasks": {"command": "copy", "value": ["Lawn"]}}`)
	handle(t, f.api, `{"tasks": {"command": "remove", "value": ["Back"]}}`)
	if got := string(topic(t, f.api.State(), "tasks")); !strings.Contains(got, `"available":["Lawn","Lawn_copy"]`) {
		t.Errorf("tasks = %s", got)
	}
	handle(t, f.api, `{"tasks": {"command": "remove", "value": [""]}}`)
	if got := f.saved.List(); len(got) != 0 {
		t.Errorf("remove all left %v", got)
	}
}
