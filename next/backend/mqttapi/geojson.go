package mqttapi

import (
	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
)

// The GeoJSON of legacy mapdata.py, with its quirks: rings are closed, the
// LineStrings of preview and mow path have one bracket more than GeoJSON
// wants ([[[x, y], …]]), a first feature without geometry names the
// collection and carries its id, and exclusions have "idx" on the feature.

type featureCollection struct {
	Type     string    `json:"type"`
	Features []feature `json:"features"`
}

type feature struct {
	Type       string         `json:"type"`
	Properties map[string]any `json:"properties"`
	Idx        *int           `json:"idx,omitempty"`
	Geometry   *geometry      `json:"geometry,omitempty"`
}

type geometry struct {
	Type        string `json:"type"`
	Coordinates any    `json:"coordinates"`
}

func collection(name string, id any, features ...feature) featureCollection {
	head := feature{Type: "Feature", Properties: map[string]any{"name": name, "id": id}}
	return featureCollection{Type: "FeatureCollection", Features: append([]feature{head}, features...)}
}

func named(name string, g geometry) feature {
	return feature{Type: "Feature", Properties: map[string]any{"name": name}, Geometry: &g}
}

func coords(pts []geo.Point) []Point {
	out := make([]Point, len(pts))
	for i, p := range pts {
		out[i] = Point{Float(p.X), Float(p.Y)}
	}
	return out
}

// closed repeats the first point at the end, like legacy perimeter_for_plot.
func closed(pts []geo.Point) []Point {
	if len(pts) == 0 {
		return []Point{}
	}
	return coords(append(append([]geo.Point{}, pts...), pts[0]))
}

func polygon(ring []Point) geometry {
	return geometry{Type: "Polygon", Coordinates: [][]Point{ring}}
}

func emptyPolygon() geometry {
	return geometry{Type: "Polygon", Coordinates: []any{}}
}

func lineString(pts []geo.Point) geometry {
	return geometry{Type: "LineString", Coordinates: coords(pts)}
}

// nestedLine is the LineString of preview and mow path: [[[x, y], …]], or []
// without points.
func nestedLine(pts []geo.Point) geometry {
	if len(pts) == 0 {
		return geometry{Type: "LineString", Coordinates: []any{}}
	}
	return geometry{Type: "LineString", Coordinates: [][]Point{coords(pts)}}
}
