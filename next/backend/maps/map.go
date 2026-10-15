// Package maps manages the garden maps (perimeter, exclusions, dock path,
// search wire), stores them as JSON, imports legacy maps and uploads a map
// to the robot.
package maps

import (
	"errors"
	"fmt"
	"math"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// MaxCoordM is the largest coordinate the robot can store: Arduino
// firmware keeps centimeters in a short (±327.67 m).
const MaxCoordM = 327

// maxNameLen keeps names readable in the UI.
const maxNameLen = 80

// Map is one garden map in meters, in the robot's local coordinate system.
type Map struct {
	ID         string        `json:"id"`
	Name       string        `json:"name"`
	Perimeter  []geo.Point   `json:"perimeter"`
	Exclusions [][]geo.Point `json:"exclusions"`
	// Dock is the path into the docking station; the last point is the station.
	Dock []geo.Point `json:"dock"`
	// SearchWire is a virtual wire the robot may use to reach the dock (optional).
	SearchWire []geo.Point `json:"searchWire"`
	UpdatedAt  time.Time   `json:"updatedAt"`
}

// ErrInvalid wraps every validation error.
var ErrInvalid = errors.New("invalid map")

// Validate checks that the map can be stored and sent to the robot.
func (m Map) Validate() error {
	m = m.normalized()
	var errs []string
	name := strings.TrimSpace(m.Name)
	if name == "" || utf8.RuneCountInString(name) > maxNameLen {
		errs = append(errs, fmt.Sprintf("name must have 1 to %d characters", maxNameLen))
	}
	if len(m.Perimeter) < 3 {
		errs = append(errs, "perimeter needs at least 3 points")
	}
	for i, ex := range m.Exclusions {
		if len(ex) < 3 {
			errs = append(errs, fmt.Sprintf("exclusion %d needs at least 3 points", i+1))
		}
	}
	if len(m.Dock) == 1 {
		errs = append(errs, "dock path needs at least 2 points or none")
	}
	if len(m.SearchWire) == 1 {
		errs = append(errs, "search wire needs at least 2 points or none")
	}
	if !m.coordsOK() {
		errs = append(errs, fmt.Sprintf("coordinates must be numbers between -%d and %d m", MaxCoordM, MaxCoordM))
	}
	if len(errs) > 0 {
		return fmt.Errorf("%w: %s", ErrInvalid, strings.Join(errs, "; "))
	}
	return nil
}

func (m Map) coordsOK() bool {
	ok := func(pts []geo.Point) bool {
		for _, p := range pts {
			for _, v := range []float64{p.X, p.Y} {
				if math.IsNaN(v) || math.Abs(v) > MaxCoordM {
					return false
				}
			}
		}
		return true
	}
	for _, ex := range m.Exclusions {
		if !ok(ex) {
			return false
		}
	}
	return ok(m.Perimeter) && ok(m.Dock) && ok(m.SearchWire)
}

// normalized trims the name, stores polygons open (without repeating the
// first point at the end, as legacy did) and replaces nil lists with empty
// ones, so the JSON never contains null for a list.
func (m Map) normalized() Map {
	m.Name = strings.TrimSpace(m.Name)
	m.Perimeter = open(nonNil(m.Perimeter))
	m.Dock = nonNil(m.Dock)
	m.SearchWire = nonNil(m.SearchWire)
	ex := make([][]geo.Point, len(m.Exclusions))
	for i, e := range m.Exclusions {
		ex[i] = open(nonNil(e))
	}
	m.Exclusions = ex
	return m
}

func open(polygon []geo.Point) []geo.Point {
	if n := len(polygon); n > 1 && polygon[0] == polygon[n-1] {
		return polygon[:n-1]
	}
	return polygon
}

func nonNil(p []geo.Point) []geo.Point {
	if p == nil {
		return []geo.Point{}
	}
	return p
}

// Robot returns the map as the robot stores it, with way as the route to
// drive. The search wire stays in CaSSAndRA (legacy does not send it either).
func (m Map) Robot(way []geo.Point) protocol.Map {
	return protocol.Map{Perimeter: m.Perimeter, Exclusions: m.Exclusions, Dock: m.Dock, Way: way}
}
