package robot

import (
	"math"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
)

// The path the robot drove since it last docked, for drawing behind it.
const (
	trailMaxPoints = 2000 // the oldest points are dropped beyond this
	trailMinStepM  = 0.05 // closer points are skipped (GPS noise, standstill)
	trailMaxJumpM  = 5.0  // a longer jump starts a new trail (relocated robot)
)

// trail is guarded by Robot.mu. Its id changes whenever it starts anew, so
// browsers know when to fetch it again instead of extending their copy.
type trail struct {
	id     int64
	points []geo.Point
}

func (t *trail) add(p geo.Point) {
	if n := len(t.points); n > 0 {
		last := t.points[n-1]
		d := math.Hypot(p.X-last.X, p.Y-last.Y)
		if d < trailMinStepM {
			return
		}
		if d > trailMaxJumpM {
			t.reset()
		}
	}
	if len(t.points) == trailMaxPoints {
		t.points = append(t.points[:0], t.points[1:]...)
	}
	t.points = append(t.points, p)
}

func (t *trail) reset() {
	t.id++
	t.points = nil
}

// TrailJSON is the trail as sent to the browser.
type TrailJSON struct {
	ID     int64       `json:"id"`
	Points []geo.Point `json:"points"`
}

// Trail returns the path driven since the robot last docked (or the trail
// was cleared).
func (r *Robot) Trail() TrailJSON {
	r.mu.Lock()
	defer r.mu.Unlock()
	return TrailJSON{ID: r.trail.id, Points: append([]geo.Point{}, r.trail.points...)}
}

// ClearTrail starts a new, empty trail.
func (r *Robot) ClearTrail() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.trail.reset()
}

// updateTrailLocked records a new state: arriving at the dock starts a new
// trail, any other online state extends it.
func (r *Robot) updateTrailLocked(before, after Status) {
	if isDockedStatus(after) && !isDockedStatus(before) {
		r.trail.reset()
	}
	if after != StatusOffline {
		r.trail.add(geo.Point{X: r.state.X, Y: r.state.Y})
	}
}

func isDockedStatus(s Status) bool {
	return s == StatusDocked || s == StatusCharging
}
