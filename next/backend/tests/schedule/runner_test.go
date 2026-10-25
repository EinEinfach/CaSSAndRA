package schedule_test

import (
	"context"
	"slices"
	"testing"
	"time"

	_ "time/tzdata" // Europe/Berlin on every machine

	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/schedule"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

const h = time.Hour

func TestStartsTheTasksOnceWhenTheWindowOpens(t *testing.T) {
	f := newFixture(t)
	f.plan(t, 0, "09:00", "12:00", "front", "back")

	f.at(9*h - time.Minute)
	if calls := f.calls(); len(calls) != 0 {
		t.Fatalf("before the window: %v", calls)
	}
	for _, at := range []time.Duration{9 * h, 9*h + time.Minute, 11 * h} {
		f.at(at)
	}
	if calls := f.calls(); !slices.Equal(calls, []string{"start"}) {
		t.Fatalf("calls = %v, want one start", calls)
	}
	if !slices.Equal(f.tasks.started[0], []string{"front", "back"}) {
		t.Errorf("started %v, want front, back in this order", f.tasks.started[0])
	}
	if st := f.runner.Status(); st.State != schedule.StateStarted || st.Message != "mowing 2 tasks until 12:00" {
		t.Errorf("status = %+v", st)
	}
}

func TestSendsTheRobotHomeOnceWhenTheWindowCloses(t *testing.T) {
	f := newFixture(t)
	f.plan(t, 0, "09:00", "12:00", "front")
	f.at(9 * h)
	f.at(12 * h)
	f.robot.set(robot.StatusMow) // still mowing, the dock did not show yet
	f.at(12*h + time.Minute)
	if calls := f.calls(); !slices.Equal(calls, []string{"start", "dock schedule"}) {
		t.Errorf("calls = %v, want start, then dock once", calls)
	}
	if st := f.runner.Status(); st.State != schedule.StateDone {
		t.Errorf("status = %+v, want done", st)
	}
}

func TestLeavesARobotAloneThatIsBackAlready(t *testing.T) {
	f := newFixture(t)
	f.plan(t, 0, "09:00", "12:00", "front")
	f.at(9 * h)
	f.robot.set(robot.StatusCharging) // route finished
	f.at(12 * h)
	if calls := f.calls(); !slices.Equal(calls, []string{"start"}) {
		t.Errorf("calls = %v, want no dock", calls)
	}
	if st := f.runner.Status(); st.State != schedule.StateDone || st.Message != "finished" {
		t.Errorf("status = %+v", st)
	}
}

func TestDoesNotSendHomeWhatItDidNotStart(t *testing.T) {
	f := newFixture(t)
	f.plan(t, 0, "09:00", "12:00", "front")
	f.robot.set(robot.StatusMow) // mowing since the morning, started by hand
	for m := 9 * h; m <= 13*h; m += 10 * time.Minute {
		f.at(m)
	}
	if calls := f.calls(); len(calls) != 0 {
		t.Errorf("calls = %v, want none", calls)
	}
	st := f.runner.Status()
	if st.State != schedule.StateFailed || st.Message != "not started: the robot stayed mow" {
		t.Errorf("status = %+v", st)
	}
}

func TestWaitsForABusyRobot(t *testing.T) {
	tests := []struct {
		name     string
		freeAt   time.Duration // the robot is idle from then on
		want     []string
		wantDone schedule.State
	}{
		{"free on the third check", 9*h + 2*time.Minute, []string{"start"}, schedule.StateStarted},
		{"busy for five checks", 9*h + 5*time.Minute, nil, schedule.StateFailed},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			f.plan(t, 0, "09:00", "12:00", "front")
			f.robot.set(robot.StatusOffline)
			for m := 9 * h; m < 9*h+10*time.Minute; m += time.Minute {
				if m == tt.freeAt {
					f.robot.set(robot.StatusIdle)
				}
				f.at(m)
				if m == 9*h {
					if st := f.runner.Status(); st.State != schedule.StateWaiting || st.Message != "waiting for the robot (offline)" {
						t.Errorf("status = %+v", st)
					}
				}
			}
			if calls := f.calls(); !slices.Equal(calls, tt.want) {
				t.Errorf("calls = %v, want %v", calls, tt.want)
			}
			if st := f.runner.Status(); st.State != tt.wantDone {
				t.Errorf("state = %q, want %q", st.State, tt.wantDone)
			}
		})
	}
}

func TestAFailedStartIsNotRepeated(t *testing.T) {
	f := newFixture(t)
	f.plan(t, 0, "09:00", "12:00", "front")
	f.tasks.err = link.ErrOffline
	for m := 9 * h; m <= 12*h; m += 30 * time.Minute {
		f.at(m)
	}
	if calls := f.calls(); !slices.Equal(calls, []string{"start"}) {
		t.Errorf("calls = %v, want a single start and no dock", calls)
	}
	if st := f.runner.Status(); st.State != schedule.StateFailed || st.Message != "start failed: "+link.ErrOffline.Error() {
		t.Errorf("status = %+v", st)
	}
}

func TestAFailedDockIsNotRepeated(t *testing.T) {
	f := newFixture(t)
	f.plan(t, 0, "09:00", "12:00", "front")
	f.at(9 * h)
	f.robot.dockErr = context.DeadlineExceeded
	f.at(12 * h)
	f.at(12*h + time.Minute)
	if calls := f.calls(); !slices.Equal(calls, []string{"start", "dock schedule"}) {
		t.Errorf("calls = %v, want one dock", calls)
	}
	if st := f.runner.Status(); st.State != schedule.StateFailed {
		t.Errorf("status = %+v, want failed", st)
	}
}

func TestWithoutTasksTheRobotContinuesItsRoute(t *testing.T) {
	f := newFixture(t)
	f.plan(t, 0, "09:00", "12:00")
	f.at(9 * h)
	if calls := f.calls(); !slices.Equal(calls, []string{"mow"}) {
		t.Errorf("calls = %v, want mow", calls)
	}
	if st := f.runner.Status(); st.Message != "mowing the route on the robot until 12:00" {
		t.Errorf("status = %+v", st)
	}
}

func TestNothingHappensWhen(t *testing.T) {
	tests := []struct {
		name  string
		setup func(t *testing.T, f *fixture)
	}{
		{"the schedule is off", func(t *testing.T, f *fixture) {
			f.plan(t, 0, "09:00", "12:00", "front")
			s := f.store.Get()
			s.Active = false
			if err := f.store.Set(s); err != nil {
				t.Fatal(err)
			}
		}},
		{"today is a day off", func(t *testing.T, f *fixture) { f.plan(t, 0, "10:00", "10:00", "front") }},
		{"another day has the window", func(t *testing.T, f *fixture) { f.plan(t, 1, "09:00", "12:00", "front") }},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			tt.setup(t, f)
			for m := 8 * h; m < 24*h; m += 15 * time.Minute {
				f.at(m)
			}
			if calls := f.calls(); len(calls) != 0 {
				t.Errorf("calls = %v", calls)
			}
		})
	}
}

func TestStartsLateButNotAfterTheWindow(t *testing.T) {
	f := newFixture(t) // e.g. the app was restarted
	f.plan(t, 0, "09:00", "12:00", "front")
	f.at(12*h + 30*time.Minute)
	if calls := f.calls(); len(calls) != 0 {
		t.Fatalf("after the window: %v", calls)
	}

	f = newFixture(t)
	f.plan(t, 0, "09:00", "12:00", "front")
	f.at(10*h + 30*time.Minute)
	if calls := f.calls(); !slices.Equal(calls, []string{"start"}) {
		t.Errorf("within the window: %v, want start", calls)
	}
}

func TestEveryDayStartsAnew(t *testing.T) {
	f := newFixture(t)
	f.plan(t, 0, "09:00", "12:00", "front")
	f.plan(t, 1, "09:00", "12:00", "back")
	f.at(9 * h)
	f.at(12 * h)
	f.robot.set(robot.StatusCharging)
	f.at(24*h + 9*h)
	if calls := f.calls(); !slices.Equal(calls, []string{"start", "dock schedule", "start"}) {
		t.Errorf("calls = %v", calls)
	}
	if !slices.Equal(f.tasks.started[1], []string{"back"}) {
		t.Errorf("Tuesday started %v, want back", f.tasks.started[1])
	}
}

func TestAWindowUntilMidnightEnds(t *testing.T) {
	f := newFixture(t)
	f.plan(t, 0, "20:00", "24:00", "front")
	f.at(20 * h)
	f.at(23*h + 59*time.Minute)
	f.at(24 * h)
	if calls := f.calls(); !slices.Equal(calls, []string{"start", "dock schedule"}) {
		t.Errorf("calls = %v, want start, then dock at midnight", calls)
	}
}

func TestStatusTellsTheNextStart(t *testing.T) {
	f := newFixture(t)
	if st := f.runner.Status(); st.State != schedule.StateOff || !st.Next.IsZero() {
		t.Errorf("inactive: %+v, want off without next", st)
	}
	f.plan(t, 0, "09:00", "12:00", "front")
	f.plan(t, 2, "07:30", "09:00", "back")

	f.at(8 * h)
	if st := f.runner.Status(); st.State != schedule.StateWaiting || !st.Next.Equal(monday.Add(9*h)) {
		t.Errorf("before the window: %+v, want waiting for Monday 09:00", st)
	}
	f.robot.set(robot.StatusMow) // busy: today's window is still to come
	f.at(9 * h)
	if st := f.runner.Status(); !st.Next.Equal(monday.Add(9 * h)) {
		t.Errorf("waiting for the robot: next = %v, want now", st.Next)
	}
	f.robot.set(robot.StatusIdle)
	f.at(9*h + time.Minute)
	if st := f.runner.Status(); !st.Next.Equal(monday.Add(2*24*h + 7*h + 30*time.Minute)) {
		t.Errorf("after starting: next = %v, want Wednesday 07:30", st.Next)
	}
}

func TestNextStartUsesTheWallClockAcrossDaylightSaving(t *testing.T) {
	berlin, err := time.LoadLocation("Europe/Berlin")
	if err != nil {
		t.Fatal(err)
	}
	f := newFixture(t)
	// Saturday 28 March 2026, 12:00; clocks go forward on Sunday at 02:00.
	clock := testkit.NewFakeClock(time.Date(2026, 3, 28, 12, 0, 0, 0, berlin))
	f.runner = schedule.NewRunner(f.store, f.robot, f.tasks, f.tasks, schedule.Config{Now: clock.Now})
	f.plan(t, 6, "09:00", "12:00", "front")
	want := time.Date(2026, 3, 29, 9, 0, 0, 0, berlin)
	if got := f.runner.Status().Next; !got.Equal(want) || got.Hour() != 9 {
		t.Errorf("next = %v, want %v", got, want)
	}
}

func TestOnChangeOnlyWhenTodayChanges(t *testing.T) {
	f := newFixture(t)
	f.plan(t, 0, "09:00", "12:00", "front")
	f.at(8 * h) // the first check of a day notifies: a new day
	n := 0
	f.runner.OnChange(func() { n++ })
	f.at(8*h + time.Minute)
	f.at(8*h + 2*time.Minute)
	if n != 0 {
		t.Errorf("before the window: %d changes, want 0", n)
	}
	f.at(9 * h)
	if n == 0 {
		t.Error("starting did not notify")
	}
	before := n
	f.at(9*h + time.Minute)
	if n != before {
		t.Error("a check without change notified")
	}
}

func TestRunChecksUntilCanceled(t *testing.T) {
	f := newFixture(t)
	f.plan(t, 0, "08:00", "12:00", "front")
	runner := schedule.NewRunner(f.store, f.robot, f.tasks, f.tasks, schedule.Config{Now: f.clock.Now, Interval: time.Millisecond})
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() { runner.Run(ctx); close(done) }()
	deadline := time.Now().Add(5 * time.Second)
	for len(f.calls()) == 0 && time.Now().Before(deadline) {
		time.Sleep(time.Millisecond)
	}
	cancel()
	<-done
	if calls := f.calls(); !slices.Equal(calls, []string{"start"}) {
		t.Errorf("calls = %v, want one start", calls)
	}
}
