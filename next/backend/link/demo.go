package link

import (
	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// DemoStation is where the demo robot charges.
var DemoStation = geo.Point{X: -1, Y: 3}

// DemoMap returns a small garden for the simulator: a 20 x 12 m lawn with a
// flower bed, a dock path ending at DemoStation and a striped mow route.
// It stands in until real maps exist.
func DemoMap() protocol.Map {
	m := protocol.Map{
		Perimeter:  []geo.Point{{X: 0, Y: 0}, {X: 20, Y: 0}, {X: 20, Y: 12}, {X: 0, Y: 12}},
		Exclusions: [][]geo.Point{{{X: 16, Y: 8}, {X: 19, Y: 8}, {X: 19, Y: 11}, {X: 16, Y: 11}}},
		Dock:       []geo.Point{{X: 1, Y: 3}, DemoStation},
	}
	// Stripes 0.5 m apart, left of the flower bed.
	for i, x := 0, 1.0; x <= 15; i, x = i+1, x+0.5 {
		if i%2 == 0 {
			m.Way = append(m.Way, geo.Point{X: x, Y: 1}, geo.Point{X: x, Y: 11})
		} else {
			m.Way = append(m.Way, geo.Point{X: x, Y: 11}, geo.Point{X: x, Y: 1})
		}
	}
	return m
}
