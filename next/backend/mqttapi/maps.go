package mqttapi

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

// MapsJSON is the payload of <prefix>/maps (legacy mapstopic.py).
type MapsJSON struct {
	Loaded    string   `json:"loaded"`
	Available []string `json:"available"`
}

func (a *API) mapsJSON() MapsJSON {
	out := MapsJSON{Available: []string{}}
	if m, ok := a.activeMap(); ok {
		out.Loaded = m.Name
	}
	for _, m := range a.maps.List() {
		out.Available = append(out.Available, m.Name)
	}
	return out
}

func (a *API) mapByName(name string) (maps.Map, error) {
	for _, m := range a.maps.List() {
		if m.Name == name {
			return m, nil
		}
	}
	return maps.Map{}, fmt.Errorf("%w: %q", maps.ErrNotFound, name)
}

// mapsCommand runs a command of the maps topic.
func (a *API) mapsCommand(ctx context.Context, c command) ([]Message, error) {
	if c.Command == "save" {
		return nil, a.saveMap(c.Value)
	}
	v, err := c.strings()
	if err != nil {
		return nil, err
	}
	name := ""
	if len(v) > 0 {
		name = v[0]
	}
	if c.Command == "select" && name == "" {
		return []Message{{"mapsCoords", []byte("{}")}}, nil
	}
	if c.Command == "rename" && len(v) < 2 {
		return nil, fmt.Errorf("%w: maps rename wants [old, new]", ErrInvalid)
	}
	switch c.Command {
	case "select", "load", "remove", "rename", "copy":
	default:
		return nil, fmt.Errorf("%w: maps command %q", ErrUnknown, c.Command)
	}
	m, err := a.mapByName(name)
	if err != nil {
		return nil, err
	}
	switch c.Command {
	case "select":
		return []Message{{"mapsCoords", mustJSON(rawMapCollection(m))}}, nil
	case "load":
		// Like legacy: show the map and send it to the robot (without a route).
		if err := a.maps.SetActive(m.ID); err != nil {
			return nil, err
		}
		return nil, a.robot.UploadMap(ctx, m.Robot(nil))
	case "remove":
		return nil, a.maps.Delete(m.ID) // its tasks go with it
	case "rename":
		m.Name = v[1]
		_, err := a.maps.Update(m)
		return nil, err
	default: // copy
		m.ID, m.Name = "", m.Name+"_copy"
		_, err := a.maps.Create(m)
		return nil, err
	}
}

// rawMapCollection is legacy maps_to_geojson: the stored points, rings not
// closed and without a naming first feature.
func rawMapCollection(m maps.Map) featureCollection {
	features := []feature{
		named("perimeter", polygon(coords(m.Perimeter))),
		named("dockpoints", lineString(m.Dock)),
		named("search wire", lineString(m.SearchWire)),
	}
	for i, e := range m.Exclusions {
		f := named("exclusion", polygon(coords(e)))
		f.Idx = &i
		features = append(features, f)
	}
	return featureCollection{Type: "FeatureCollection", Features: features}
}

// saveMap stores a map from the native editor under a new name and, given
// its old name, copies the tasks of the old map (legacy import_api_map).
func (a *API) saveMap(raw json.RawMessage) error {
	var fc struct {
		Features []struct {
			Properties struct {
				Name    string `json:"name"`
				OldName string `json:"oldName"`
			} `json:"properties"`
			Geometry struct {
				Coordinates [][]float64 `json:"coordinates"`
			} `json:"geometry"`
		} `json:"features"`
	}
	if err := json.Unmarshal(raw, &fc); err != nil {
		return fmt.Errorf("%w: maps save wants a FeatureCollection: %w", ErrInvalid, err)
	}
	if len(fc.Features) == 0 {
		return fmt.Errorf("%w: maps save without features", ErrInvalid)
	}
	head := fc.Features[0].Properties
	if head.Name == "" {
		return fmt.Errorf("%w: maps save without a name", ErrInvalid)
	}
	if _, err := a.mapByName(head.Name); err == nil {
		return fmt.Errorf("%w: %q", maps.ErrNameTaken, head.Name)
	}
	m := maps.Map{Name: head.Name, Exclusions: [][]geo.Point{}}
	for _, f := range fc.Features[1:] {
		pts, err := pointList(f.Geometry.Coordinates)
		if err != nil {
			return err
		}
		switch f.Properties.Name {
		case "perimeter":
			m.Perimeter = openRing(pts)
		case "exclusion":
			m.Exclusions = append(m.Exclusions, openRing(pts))
		case "dockPath":
			m.Dock = pts
		case "searchWire":
			m.SearchWire = pts
		}
	}
	created, err := a.maps.Create(m)
	if err != nil {
		return err
	}
	if head.OldName == "" || head.OldName == head.Name {
		return nil
	}
	old, err := a.mapByName(head.OldName)
	if err != nil {
		return nil //nolint:nilerr // a new map has no tasks to copy
	}
	var errs []error
	for _, t := range a.saved.List() {
		if t.MapID == old.ID {
			t.ID, t.MapID = "", created.ID
			if _, err := a.saved.Create(t); err != nil {
				errs = append(errs, err)
			}
		}
	}
	return errors.Join(errs...)
}

func pointList(c [][]float64) ([]geo.Point, error) {
	out := make([]geo.Point, len(c))
	for i, p := range c {
		if len(p) < 2 {
			return nil, fmt.Errorf("%w: a point needs x and y", ErrInvalid)
		}
		out[i] = geo.Point{X: p[0], Y: p[1]}
	}
	return out, nil
}

// openRing drops the closing point of a ring.
func openRing(pts []geo.Point) []geo.Point {
	if n := len(pts); n > 1 && pts[0] == pts[n-1] {
		return pts[:n-1]
	}
	return pts
}

// SavedTasks is what the API needs from the task store.
type SavedTasks interface {
	List() []tasks.Task
	Get(id string) (tasks.Task, error)
	Create(t tasks.Task) (tasks.Task, error)
	Update(t tasks.Task) (tasks.Task, error)
	Delete(id string) error
}
