// Package geo provides the shared geometry types (points, polygons, line strings) in meters.
package geo

// Point is a position in the robot's local coordinate system, in meters.
type Point struct {
	X, Y float64
}
