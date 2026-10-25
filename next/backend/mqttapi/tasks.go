package mqttapi

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

// TasksJSON is the payload of <prefix>/tasks (legacy taskstopic.py): task
// names of the active map.
type TasksJSON struct {
	Selected  []string `json:"selected"`
	Loaded    []string `json:"loaded"`
	Available []string `json:"available"`
}

func (a *API) tasksJSON() TasksJSON {
	a.mu.Lock()
	selected, loaded := a.selectedTasks, a.loadedTasks
	a.mu.Unlock()
	out := TasksJSON{Selected: a.taskNames(selected), Loaded: a.taskNames(loaded), Available: []string{}}
	for _, t := range a.activeTasks() {
		out.Available = append(out.Available, t.Name)
	}
	return out
}

func (a *API) taskNames(ids []string) []string {
	out := []string{}
	for _, id := range ids {
		if t, err := a.saved.Get(id); err == nil {
			out = append(out, t.Name)
		}
	}
	return out
}

// activeTasks are the tasks of the active map.
func (a *API) activeTasks() []tasks.Task {
	id := a.maps.ActiveID()
	var out []tasks.Task
	for _, t := range a.saved.List() {
		if t.MapID == id && id != "" {
			out = append(out, t)
		}
	}
	return out
}

// taskIDs finds the tasks of the active map by name, in the given order;
// unknown names are left out, like legacy.
func (a *API) taskIDs(names []string) []string {
	active := a.activeTasks()
	ids := []string{}
	for _, n := range names {
		for _, t := range active {
			if t.Name == n {
				ids = append(ids, t.ID)
				break
			}
		}
	}
	return ids
}

// tasksCommand runs a command of the tasks topic.
func (a *API) tasksCommand(ctx context.Context, c command) ([]Message, error) {
	switch c.Command {
	case "save":
		return nil, a.saveTask(c.Value)
	case "calculate":
		return a.calculate(ctx, c.Value)
	}
	names, err := c.strings()
	if err != nil {
		return nil, err
	}
	switch c.Command {
	case "select":
		ids := a.taskIDs(names)
		a.mu.Lock()
		a.selectedTasks = ids
		a.mu.Unlock()
		var out []Message
		for _, id := range ids {
			if t, err := a.saved.Get(id); err == nil {
				out = append(out, Message{"coords", mustJSON(a.taskCollection(ctx, t))})
			}
		}
		return out, nil
	case "load":
		return nil, a.loadTasks(ctx, a.taskIDs(names))
	case "remove":
		return nil, a.removeTasks(names)
	case "rename":
		if len(names) < 2 {
			return nil, fmt.Errorf("%w: tasks rename wants [old, new]", ErrInvalid)
		}
		t, err := a.taskByName(names[0])
		if err != nil {
			return nil, err
		}
		t.Name = names[1]
		_, err = a.saved.Update(t)
		return nil, err
	case "copy":
		if len(names) == 0 {
			return nil, fmt.Errorf("%w: tasks copy wants [name]", ErrInvalid)
		}
		t, err := a.taskByName(names[0])
		if err != nil {
			return nil, err
		}
		t.ID, t.Name = "", t.Name+"_copy"
		_, err = a.saved.Create(t)
		return nil, err
	}
	return nil, fmt.Errorf("%w: tasks command %q", ErrUnknown, c.Command)
}

func (a *API) taskByName(name string) (tasks.Task, error) {
	for _, t := range a.activeTasks() {
		if t.Name == name {
			return t, nil
		}
	}
	return tasks.Task{}, fmt.Errorf("%w: %q", tasks.ErrNotFound, name)
}

// loadTasks selects the tasks, computes their route and sends it with the
// map to the robot without starting it (legacy "load").
func (a *API) loadTasks(ctx context.Context, ids []string) error {
	if len(ids) == 0 {
		return fmt.Errorf("%w: no known task to load", ErrInvalid)
	}
	plan, err := a.tasks.Preview(ctx, tasks.Request{TaskIDs: ids})
	if err != nil {
		return err
	}
	m, err := a.maps.Get(plan.MapID)
	if err != nil {
		return err
	}
	a.mu.Lock()
	a.selectedTasks, a.loadedTasks = ids, ids
	a.mu.Unlock()
	return a.robot.UploadMap(ctx, m.Robot(plan.Route))
}

// removeTasks deletes a task by name; "" deletes every task of the map.
func (a *API) removeTasks(names []string) error {
	if len(names) == 0 {
		return fmt.Errorf("%w: tasks remove wants [name]", ErrInvalid)
	}
	var errs []error
	for _, t := range a.activeTasks() {
		if names[0] == "" || t.Name == names[0] {
			errs = append(errs, a.saved.Delete(t.ID))
		}
	}
	a.mu.Lock()
	a.selectedTasks = nil
	a.mu.Unlock()
	return errors.Join(errs...)
}

// subtask is a part as the native app sends it.
type subtask struct {
	Properties struct {
		SubtaskNr     *int            `json:"subtaskNr"`
		MowParameters json.RawMessage `json:"mowParameters"`
	} `json:"properties"`
	Geometry json.RawMessage `json:"geometry"`
}

type ring struct {
	Coordinates [][][]float64 `json:"coordinates"`
}

func (r ring) points() ([]geo.Point, error) {
	if len(r.Coordinates) == 0 {
		return nil, nil
	}
	pts, err := pointList(r.Coordinates[0])
	return openRing(pts), err
}

// saveTask stores a task of the active map under a new name; each part has
// its selection and parameters (the preview route is computed again later).
func (a *API) saveTask(raw json.RawMessage) error {
	var fc struct {
		Features []json.RawMessage `json:"features"`
	}
	if err := json.Unmarshal(raw, &fc); err != nil || len(fc.Features) == 0 {
		return fmt.Errorf("%w: tasks save wants a FeatureCollection", ErrInvalid)
	}
	var head struct {
		Properties struct {
			TaskName string `json:"taskName"`
		} `json:"properties"`
	}
	if err := json.Unmarshal(fc.Features[0], &head); err != nil || head.Properties.TaskName == "" {
		return fmt.Errorf("%w: tasks save without a task name", ErrInvalid)
	}
	mapID := a.maps.ActiveID()
	if mapID == "" {
		return tasks.ErrNoMap
	}
	if _, err := a.taskByName(head.Properties.TaskName); err == nil {
		return fmt.Errorf("%w: %q", tasks.ErrNameTaken, head.Properties.TaskName)
	}
	t := tasks.Task{Name: head.Properties.TaskName, MapID: mapID}
	for _, raw := range fc.Features[1:] {
		var st subtask
		// The app sends a bare list for a part without selection; legacy
		// could not read it either.
		if err := json.Unmarshal(raw, &st); err != nil || st.Properties.SubtaskNr == nil {
			continue
		}
		var geoms []ring
		if err := json.Unmarshal(st.Geometry, &geoms); err != nil || len(geoms) == 0 {
			return fmt.Errorf("%w: tasks save: part %d has no selection", ErrInvalid, *st.Properties.SubtaskNr)
		}
		sel, err := geoms[0].points()
		if err != nil {
			return err
		}
		p, err := a.partParameters(st.Properties.MowParameters)
		if err != nil {
			return err
		}
		t.Parts = append(t.Parts, tasks.Part{Selection: sel, Parameters: p})
	}
	_, err := a.saved.Create(t)
	return err
}

func (a *API) partParameters(raw json.RawMessage) (tasks.Parameters, error) {
	a.mu.Lock()
	base := a.parameters
	a.mu.Unlock()
	return fromParametersJSON(raw, base)
}

// calculate computes the route of one part the app is editing and answers
// on coords with the request, renamed "taskPreview", its second feature's
// geometry replaced by the route (legacy taskstopic.py _calculate).
func (a *API) calculate(ctx context.Context, raw json.RawMessage) ([]Message, error) {
	var fc struct {
		Features []json.RawMessage `json:"features"`
	}
	if err := json.Unmarshal(raw, &fc); err != nil || len(fc.Features) < 2 {
		return nil, fmt.Errorf("%w: tasks calculate wants a FeatureCollection with the part", ErrInvalid)
	}
	var st subtask
	if err := json.Unmarshal(fc.Features[1], &st); err != nil {
		return nil, fmt.Errorf("%w: tasks calculate: %w", ErrInvalid, err)
	}
	var g ring
	if err := json.Unmarshal(st.Geometry, &g); err != nil {
		return nil, fmt.Errorf("%w: tasks calculate: the part needs a Polygon", ErrInvalid)
	}
	sel, err := g.points()
	if err != nil {
		return nil, err
	}
	p, err := a.partParameters(st.Properties.MowParameters)
	if err != nil {
		return nil, err
	}
	plan, err := a.tasks.Compute(ctx, tasks.Request{Parts: []tasks.Part{{Selection: sel, Parameters: p}}})
	if err != nil {
		return nil, err
	}

	// Echo the request as it came (numbers untouched), with the two changes.
	var echo map[string]any
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	if err := dec.Decode(&echo); err != nil {
		return nil, fmt.Errorf("%w: %w", ErrInvalid, err)
	}
	features, _ := echo["features"].([]any)
	first, _ := features[0].(map[string]any)
	second, _ := features[1].(map[string]any)
	if first == nil || second == nil {
		return nil, fmt.Errorf("%w: tasks calculate: features must be objects", ErrInvalid)
	}
	props, _ := first["properties"].(map[string]any)
	if props == nil {
		props = map[string]any{}
		first["properties"] = props
	}
	props["name"] = "taskPreview"
	second["geometry"] = nestedLine(plan.Route)
	return []Message{{"coords", mustJSON(echo)}}, nil
}

// taskCollection is legacy task_to_gejson: per part its route and its
// selection with the mow parameters.
func (a *API) taskCollection(ctx context.Context, t tasks.Task) featureCollection {
	m, _ := a.maps.Get(t.MapID)
	head := feature{Type: "Feature", Properties: map[string]any{"name": "task", "id": t.Name, "mapName": m.Name}}
	fc := featureCollection{Type: "FeatureCollection", Features: []feature{head}}
	for i, part := range t.Parts {
		var route []geo.Point
		if plan, err := a.tasks.Compute(ctx, tasks.Request{Parts: []tasks.Part{part}}); err == nil {
			route = plan.Route
		}
		preview := named("", nestedLine(route))
		preview.Properties = map[string]any{"name": i}
		fc.Features = append(fc.Features, preview, selectionFeature(i, part, m))
	}
	return fc
}

func selectionFeature(i int, part tasks.Part, m maps.Map) feature {
	props := map[string]any{"name": i}
	pj := parametersJSON(part.Parameters)
	b, _ := json.Marshal(pj)
	var flat map[string]json.RawMessage
	_ = json.Unmarshal(b, &flat)
	for k, v := range flat {
		props[k] = v
	}
	g := polygon(closed(part.Selection))
	props["type"] = "lasso"
	if len(part.Selection) == 0 {
		props["type"] = "map"
		g = polygon(coords(m.Perimeter))
	}
	return feature{Type: "Feature", Properties: props, Geometry: &g}
}
