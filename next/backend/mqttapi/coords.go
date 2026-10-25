package mqttapi

import (
	"fmt"
	"slices"

	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
)

// coordsCommand answers {"coords": {"command": "update", "value": [...]}}
// with one <prefix>/coords message per requested item.
func (a *API) coordsCommand(c command) ([]Message, error) {
	if c.Command != "update" {
		return nil, fmt.Errorf("%w: coords command %q", ErrUnknown, c.Command)
	}
	items, err := c.strings()
	if err != nil {
		return nil, err
	}
	var out []Message
	// In the legacy order, whatever order was asked for.
	for _, item := range []string{"currentMap", "preview", "mowPath", "obstacles"} {
		if !slices.Contains(items, item) {
			continue
		}
		var fc featureCollection
		switch item {
		case "currentMap":
			m, ok := a.activeMap()
			fc = mapCollection("current map", mapID(m, ok), m, ok)
		case "preview":
			p := a.tasks.Current()
			var route = nestedLine(nil)
			if p != nil {
				route = nestedLine(p.Route)
			}
			fc = collection("current preview", previewID(p), named("preview", route))
		case "mowPath":
			way := a.robot.Map().Way
			fc = collection("current mow path", pointsID(way), named("mow path", nestedLine(way)))
		case "obstacles":
			obstacles := a.robot.Snapshot().Obstacles
			var features []feature
			for _, o := range obstacles {
				features = append(features, named("obstacle", polygon(coords(o))))
			}
			if len(features) == 0 {
				features = []feature{named("obstacle", emptyPolygon())}
			}
			fc = collection("obstacles", pointsID(obstacles...), features...)
		}
		out = append(out, Message{"coords", mustJSON(fc)})
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("%w: coords update wants currentMap, preview, mowPath or obstacles", ErrInvalid)
	}
	return out, nil
}

// mapCollection is a map in legacy GeoJSON (perimeter_to_geojson).
func mapCollection(name string, id any, m maps.Map, ok bool) featureCollection {
	if !ok {
		return collection(name, id, named("perimeter", emptyPolygon()))
	}
	return collection(name, id, mapFeatures(m)...)
}

// mapFeatures are perimeter, dock path, search wire and exclusions.
func mapFeatures(m maps.Map) []feature {
	features := []feature{
		named("perimeter", polygon(closed(m.Perimeter))),
		named("dockpoints", lineString(m.Dock)),
		named("search wire", lineString(m.SearchWire)),
	}
	for i, e := range m.Exclusions {
		f := named("exclusion", polygon(closed(e)))
		f.Idx = &i
		features = append(features, f)
	}
	return features
}
