package mqttapi_test

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/mqttapi"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

// fakeRobot records the commands and reports the snapshot it is given.
type fakeRobot struct {
	mu    sync.Mutex
	snap  robot.Snapshot
	route protocol.Map // the map on the robot
	calls []string
	err   error
	// block makes Mow wait until it is closed (a long command).
	block chan struct{}
}

func (r *fakeRobot) Snapshot() robot.Snapshot {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.snap
}

func (r *fakeRobot) set(f func(s *robot.Snapshot)) {
	r.mu.Lock()
	defer r.mu.Unlock()
	f(&r.snap)
}

func (r *fakeRobot) record(call string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.calls = append(r.calls, call)
	return r.err
}

func (r *fakeRobot) recorded() []string {
	r.mu.Lock()
	defer r.mu.Unlock()
	return append([]string(nil), r.calls...)
}

func (r *fakeRobot) Stop(context.Context) error { return r.record("stop") }
func (r *fakeRobot) Dock(context.Context) error { return r.record("dock") }
func (r *fakeRobot) Mow(ctx context.Context) error {
	if r.block != nil {
		select {
		case <-r.block:
		case <-ctx.Done():
		}
	}
	return r.record("mow")
}
func (r *fakeRobot) Move(_ context.Context, lin, ang float64) error {
	return r.record("move " + ftoa(lin) + " " + ftoa(ang))
}
func (r *fakeRobot) SetSpeed(_ context.Context, mps float64) error {
	return r.record("speed " + ftoa(mps))
}
func (r *fakeRobot) SetMowMotor(_ context.Context, on bool) error {
	if on {
		return r.record("mow motor on")
	}
	return r.record("mow motor off")
}
func (r *fakeRobot) SkipNextPoint(context.Context) error { return r.record("skip next point") }
func (r *fakeRobot) SkipToProgress(_ context.Context, f float64) error {
	return r.record("skip to " + ftoa(f))
}
func (r *fakeRobot) Reboot(context.Context) error    { return r.record("reboot") }
func (r *fakeRobot) RebootGPS(context.Context) error { return r.record("reboot gps") }
func (r *fakeRobot) Shutdown(context.Context) error  { return r.record("shutdown") }
func (r *fakeRobot) Map() protocol.Map {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.route
}
func (r *fakeRobot) ClearObstacles() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.snap.Obstacles = nil
	r.calls = append(r.calls, "clear obstacles")
}

// fakeTasks records its commands on the robot's call list.
type fakeTasks struct {
	robot    *fakeRobot
	mu       sync.Mutex
	plan     *tasks.Plan
	requests []tasks.Request
	err      error
}

func (t *fakeTasks) Goto(_ context.Context, goal geo.Point) ([]geo.Point, error) {
	return []geo.Point{goal}, t.robot.record("goto " + ftoa(goal.X) + "," + ftoa(goal.Y))
}

func (t *fakeTasks) Current() *tasks.Plan {
	t.mu.Lock()
	defer t.mu.Unlock()
	return t.plan
}

func (t *fakeTasks) Clear() {
	t.mu.Lock()
	t.plan = nil
	t.mu.Unlock()
	_ = t.robot.record("clear plan")
}

func (t *fakeTasks) PlanAndStart(_ context.Context, req tasks.Request) (tasks.Plan, error) {
	t.mu.Lock()
	t.requests = append(t.requests, req)
	err := t.err
	t.mu.Unlock()
	return tasks.Plan{}, errors.Join(t.robot.record("plan and start"), err)
}

// fakeMaps holds maps by id.
type fakeMaps struct {
	active string
	maps   map[string]maps.Map
}

func (m *fakeMaps) ActiveID() string { return m.active }
func (m *fakeMaps) Get(id string) (maps.Map, error) {
	if mm, ok := m.maps[id]; ok {
		return mm, nil
	}
	return maps.Map{}, maps.ErrNotFound
}

// garden is a map with every kind of line.
func garden() maps.Map {
	return maps.Map{
		ID: "g1", Name: "Garden", UpdatedAt: t0,
		Perimeter:  []geo.Point{{X: 0, Y: 0}, {X: 10, Y: 0}, {X: 10, Y: 8}, {X: 0, Y: 8}},
		Exclusions: [][]geo.Point{{{X: 2, Y: 2}, {X: 3, Y: 2}, {X: 3, Y: 3}}},
		Dock:       []geo.Point{{X: 1, Y: 1}, {X: 1, Y: -1.5}},
		SearchWire: []geo.Point{{X: 5, Y: 0}, {X: 5, Y: 4}},
	}
}

var defaults = tasks.Parameters{Pattern: "lines", WidthM: 0.18, MowArea: true, BorderLaps: 1, DistanceToBorder: 1}

// newAPI is the API with a robot mowing in the garden.
func newAPI(t *testing.T) (*mqttapi.API, *fakeRobot, *fakeTasks, *fakeMaps) {
	t.Helper()
	r := &fakeRobot{snap: mowing()}
	ft := &fakeTasks{robot: r}
	fm := &fakeMaps{active: "g1", maps: map[string]maps.Map{"g1": garden()}}
	return mqttapi.New(mqttapi.Deps{Robot: r, Tasks: ft, Maps: fm, Defaults: defaults}, mqttapi.Config{Version: "test"}), r, ft, fm
}

func ftoa(f float64) string {
	b, _ := (mqttFloat(f)).MarshalJSON()
	return string(b)
}

var t0 = time.Date(2026, 10, 26, 9, 0, 0, 0, time.UTC)
