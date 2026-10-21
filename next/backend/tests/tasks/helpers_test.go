package tasks_test

import (
	"context"
	"path/filepath"
	"sync"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

var t0 = time.Date(2026, 5, 1, 10, 0, 0, 0, time.UTC)

// garden is 10 x 10 m; the dock path leads from (2, 1) to the station at (2, -1).
var garden = maps.Map{
	Name:       "garden",
	Perimeter:  []geo.Point{{X: 0, Y: 0}, {X: 10, Y: 0}, {X: 10, Y: 10}, {X: 0, Y: 10}},
	Exclusions: [][]geo.Point{{{X: 4, Y: 4}, {X: 6, Y: 4}, {X: 6, Y: 6}, {X: 4, Y: 6}}},
	Dock:       []geo.Point{{X: 2, Y: 1}, {X: 2, Y: -1}},
	SearchWire: []geo.Point{{X: 1, Y: 1}, {X: 9, Y: 1}},
}

var params = tasks.Parameters{
	Pattern: tasks.PatternLines, WidthM: 0.2, AngleDeg: 90, DistanceToBorder: 2,
	MowArea: true, BorderLaps: 1, MowExclusions: true,
}

// fakeRobot reports a fixed snapshot and records what it is sent.
type fakeRobot struct {
	mu        sync.Mutex
	snap      robot.Snapshot
	uploads   []protocol.Map
	calls     []string // "upload", "mow", "goto" in order
	uploadErr error
	mowErr    error // Mow and Goto
	// uploading, if set, is closed when an upload starts; the upload then
	// waits for release.
	uploading, release chan struct{}
}

func (f *fakeRobot) UploadMap(ctx context.Context, m protocol.Map) error {
	f.mu.Lock()
	f.uploads = append(f.uploads, m)
	f.calls = append(f.calls, "upload")
	err, uploading, release := f.uploadErr, f.uploading, f.release
	f.mu.Unlock()
	if uploading != nil {
		close(uploading)
		select {
		case <-release:
		case <-ctx.Done():
			return ctx.Err()
		}
	}
	return err
}

func (f *fakeRobot) Mow(context.Context) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.calls = append(f.calls, "mow")
	return f.mowErr
}

func (f *fakeRobot) Goto(context.Context) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.calls = append(f.calls, "goto")
	return f.mowErr
}

func (f *fakeRobot) sent() ([]string, []protocol.Map) {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]string(nil), f.calls...), append([]protocol.Map(nil), f.uploads...)
}

func (f *fakeRobot) Snapshot() robot.Snapshot {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.snap
}

func (f *fakeRobot) set(pos geo.Point, op protocol.Op) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.snap.Position, f.snap.Op = pos, op
}

type fixture struct {
	maps    *maps.Store
	mapID   string
	robot   *fakeRobot
	planner *testkit.FakePlanner
	clock   *testkit.FakeClock
	tasks   *tasks.Store
	svc     *tasks.Service
}

// newFixture has the garden as active map and the robot idle at (5, 2).
func newFixture(t *testing.T) *fixture {
	t.Helper()
	clock := testkit.NewFakeClock(t0)
	store, err := maps.OpenStore(t.TempDir(), maps.StoreConfig{Now: clock.Now})
	if err != nil {
		t.Fatal(err)
	}
	m, err := store.Create(garden)
	if err != nil {
		t.Fatal(err)
	}
	if err := store.SetActive(m.ID); err != nil {
		t.Fatal(err)
	}
	f := &fixture{maps: store, mapID: m.ID, robot: &fakeRobot{}, planner: &testkit.FakePlanner{}, clock: clock}
	f.robot.set(geo.Point{X: 5, Y: 2}, protocol.OpIdle)
	f.tasks, err = tasks.OpenStore(filepath.Join(t.TempDir(), "tasks.json"), tasks.StoreConfig{Now: clock.Now})
	if err != nil {
		t.Fatal(err)
	}
	f.svc = tasks.New(f.planner, store, f.robot, f.tasks, tasks.Config{Now: clock.Now})
	return f
}

// one is a request for one part.
func one(sel []geo.Point, p tasks.Parameters) tasks.Request {
	return tasks.Request{Parts: []tasks.Part{{Selection: sel, Parameters: p}}}
}
