package mqttapi_test

import (
	"context"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
)

// fakeRobot records the commands and reports the snapshot it is given.
type fakeRobot struct {
	mu    sync.Mutex
	snap  robot.Snapshot
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

// fakeTasks records goto goals on the robot's call list.
type fakeTasks struct{ robot *fakeRobot }

func (t *fakeTasks) Goto(_ context.Context, goal geo.Point) ([]geo.Point, error) {
	return []geo.Point{goal}, t.robot.record("goto " + ftoa(goal.X) + "," + ftoa(goal.Y))
}

func ftoa(f float64) string {
	b, _ := (mqttFloat(f)).MarshalJSON()
	return string(b)
}

var t0 = time.Date(2026, 10, 26, 9, 0, 0, 0, time.UTC)
