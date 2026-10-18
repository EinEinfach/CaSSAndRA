package robot_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
)

func at(op protocol.Op, x, y float64) protocol.State {
	s := state(op)
	s.X, s.Y = x, y
	return s
}

func charging(x, y float64) protocol.State {
	s := at(protocol.OpCharge, x, y)
	s.Amps = -1
	return s
}

func TestTrailFollowsTheRobot(t *testing.T) {
	f := newFixture(t)
	f.online(at(protocol.OpMow, 0, 0))
	for _, s := range []protocol.State{
		at(protocol.OpMow, 0.01, 0), // GPS noise: skipped
		at(protocol.OpMow, 1, 0),
		at(protocol.OpMow, 2, 0),
	} {
		f.robot.OnState(s)
	}
	if got := f.robot.Trail(); !reflect.DeepEqual(got.Points, pts(0, 0, 1, 0, 2, 0)) || got.ID != t0.UnixMilli() {
		t.Errorf("trail = %+v", got)
	}
}

func TestTrailStartsAnewWhenTheRobotDocks(t *testing.T) {
	f := newFixture(t)
	f.online(at(protocol.OpMow, 0, 0))
	f.robot.OnState(at(protocol.OpDock, 3, 0))
	before := f.robot.Trail()

	f.robot.OnState(charging(4, 0))
	got := f.robot.Trail()
	if got.ID == before.ID || !reflect.DeepEqual(got.Points, pts(4, 0)) {
		t.Fatalf("after docking: %+v (before %+v), want a new trail from the dock", got, before)
	}

	// Staying in the dock keeps the trail; leaving it extends it.
	f.robot.OnState(charging(4, 0))
	f.robot.OnState(at(protocol.OpIdle, 3, 0))
	if after := f.robot.Trail(); after.ID != got.ID || len(after.Points) != 2 {
		t.Errorf("after leaving the dock: %+v", after)
	}
}

func TestTrailStartsAnewAfterAJump(t *testing.T) {
	f := newFixture(t)
	f.online(at(protocol.OpMow, 0, 0))
	id := f.robot.Trail().ID
	f.robot.OnState(at(protocol.OpMow, 10, 0))
	if got := f.robot.Trail(); got.ID == id || !reflect.DeepEqual(got.Points, pts(10, 0)) {
		t.Errorf("after a 10 m jump: %+v", got)
	}
}

func TestTrailKeepsTheNewestPoints(t *testing.T) {
	f := newFixture(t)
	f.robot.OnOnline(true)
	for i := range 2100 {
		f.robot.OnState(at(protocol.OpMow, float64(i)*0.1, 0))
	}
	got := f.robot.Trail().Points
	if len(got) != 2000 || got[0] != (geo.Point{X: 10, Y: 0}) {
		t.Errorf("%d points starting at %v, want 2000 starting at (10,0)", len(got), got[0])
	}
}

func TestTrailIgnoresOfflineStates(t *testing.T) {
	f := newFixture(t)
	f.robot.OnState(at(protocol.OpMow, 1, 1)) // not connected
	if got := f.robot.Trail().Points; len(got) != 0 {
		t.Errorf("trail while offline = %v", got)
	}
}

func TestTrailAPI(t *testing.T) {
	f := newFixture(t)
	f.online(at(protocol.OpMow, 0, 0))
	f.robot.OnState(at(protocol.OpMow, 1, 0))
	h := f.robot.Handler()

	get := func() robot.TrailJSON {
		t.Helper()
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/api/robot/trail", nil))
		var tr robot.TrailJSON
		if rec.Code != http.StatusOK || json.Unmarshal(rec.Body.Bytes(), &tr) != nil {
			t.Fatalf("GET trail = %d %s", rec.Code, rec.Body)
		}
		return tr
	}
	before := get()
	if len(before.Points) != 2 {
		t.Fatalf("trail = %+v", before)
	}

	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodDelete, "/api/robot/trail", nil))
	if rec.Code != http.StatusNoContent {
		t.Fatalf("DELETE trail = %d", rec.Code)
	}
	after := get()
	if after.ID == before.ID || after.Points == nil || len(after.Points) != 0 {
		t.Errorf("after clearing: %+v; want a new id and an empty list (not null)", after)
	}
	if id := f.robot.StateJSON().TrailID; id != after.ID {
		t.Errorf("state trailId = %d, want %d", id, after.ID)
	}
}
