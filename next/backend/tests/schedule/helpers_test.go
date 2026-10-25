package schedule_test

import (
	"context"
	"path/filepath"
	"slices"
	"sync"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/schedule"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

// monday is 26 October 2026, a Monday, at midnight in local time.
var monday = time.Date(2026, 10, 26, 0, 0, 0, 0, time.Local)

// fakeRobot records commands and reports the status it is given.
type fakeRobot struct {
	mu      sync.Mutex
	status  robot.Status
	calls   []string
	mowErr  error
	dockErr error
}

func (r *fakeRobot) Snapshot() robot.Snapshot {
	r.mu.Lock()
	defer r.mu.Unlock()
	return robot.Snapshot{Status: r.status, Online: r.status != robot.StatusOffline}
}

func (r *fakeRobot) Mow(context.Context) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.calls = append(r.calls, "mow")
	if r.mowErr == nil {
		r.status = robot.StatusMow
	}
	return r.mowErr
}

func (r *fakeRobot) DockFor(_ context.Context, reason robot.DockReason) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.calls = append(r.calls, "dock "+string(reason))
	if r.dockErr == nil {
		r.status = robot.StatusDocking
	}
	return r.dockErr
}

func (r *fakeRobot) set(s robot.Status) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.status = s
}

// fakeTasks starts tasks on fakeRobot and knows the saved tasks.
type fakeTasks struct {
	robot   *fakeRobot
	saved   map[string]tasks.Task
	started [][]string
	err     error
}

func (f *fakeTasks) PlanAndStart(_ context.Context, req tasks.Request) (tasks.Plan, error) {
	f.robot.mu.Lock()
	defer f.robot.mu.Unlock()
	f.started = append(f.started, req.TaskIDs)
	f.robot.calls = append(f.robot.calls, "start")
	if f.err != nil {
		return tasks.Plan{}, f.err
	}
	f.robot.status = robot.StatusMow
	return tasks.Plan{TaskIDs: req.TaskIDs}, nil
}

func (f *fakeTasks) Get(id string) (tasks.Task, error) {
	t, ok := f.saved[id]
	if !ok {
		return tasks.Task{}, tasks.ErrNotFound
	}
	return t, nil
}

type fixture struct {
	store  *schedule.Store
	robot  *fakeRobot
	tasks  *fakeTasks
	clock  *testkit.FakeClock
	runner *schedule.Runner
}

func newFixture(t *testing.T) *fixture {
	t.Helper()
	store, err := schedule.OpenStore(filepath.Join(t.TempDir(), "schedule.json"))
	if err != nil {
		t.Fatal(err)
	}
	r := &fakeRobot{status: robot.StatusCharging}
	ft := &fakeTasks{robot: r, saved: map[string]tasks.Task{
		"front": {ID: "front", MapID: "garden"},
		"back":  {ID: "back", MapID: "garden"},
		"other": {ID: "other", MapID: "yard"},
	}}
	clock := testkit.NewFakeClock(monday.Add(8 * time.Hour))
	f := &fixture{store: store, robot: r, tasks: ft, clock: clock}
	f.runner = schedule.NewRunner(store, r, ft, ft, schedule.Config{Now: clock.Now})
	return f
}

// plan activates a schedule with day i (0 = Monday) from start to end.
func (f *fixture) plan(t *testing.T, i int, start, end string, taskIDs ...string) {
	t.Helper()
	s := f.store.Get()
	s.Active = true
	s.Days[i] = schedule.Day{Start: start, End: end, TaskIDs: taskIDs}
	if err := f.store.Set(s); err != nil {
		t.Fatal(err)
	}
}

// at sets the clock to monday + d and checks the schedule.
func (f *fixture) at(d time.Duration) {
	f.clock.Advance(monday.Add(d).Sub(f.clock.Now()))
	f.runner.Check(context.Background())
}

func (f *fixture) calls() []string {
	f.robot.mu.Lock()
	defer f.robot.mu.Unlock()
	return slices.Clone(f.robot.calls)
}
