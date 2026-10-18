//go:build !cpp

package planner

import "github.com/EinEinfach/CaSSAndRA/next/backend/geo"

const available = false

func version() string { return "" }

func route(Area, Settings, geo.Point) ([]geo.Point, error) { return nil, ErrUnavailable }

func way(Area, geo.Point, geo.Point) ([]geo.Point, error) { return nil, ErrUnavailable }
