package schedule

import (
	"context"
	"fmt"
	"log/slog"
	"slices"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

// Robot is what the schedule needs from the robot.
type Robot interface {
	Snapshot() robot.Snapshot
	Mow(ctx context.Context) error
	DockFor(ctx context.Context, reason robot.DockReason) error
}

// Tasks starts the route of saved tasks.
type Tasks interface {
	PlanAndStart(ctx context.Context, req tasks.Request) (tasks.Plan, error)
}

// TaskStore finds saved tasks.
type TaskStore interface {
	Get(id string) (tasks.Task, error)
}

// startTimeout covers computing the route, sending it and the mow command;
// dockTimeout the dock command.
const (
	startTimeout = 5 * time.Minute
	dockTimeout  = time.Minute
)

// Config holds the injectable parts of a Runner.
type Config struct {
	Now func() time.Time
	// Interval between two checks (default one minute, like legacy).
	Interval time.Duration
	// MaxWaits is how many checks the start waits for a robot that is busy or
	// offline before it gives up for the day (default 5, like legacy).
	MaxWaits int
	Logger   *slog.Logger
}

// State is where today's window stands.
type State string

// The states of Status.
const (
	StateOff     State = "off"     // schedule inactive or a day off
	StateWaiting State = "waiting" // the window has not started, or the robot is busy
	StateStarted State = "started" // mowing was started, the robot is sent home at the end
	StateDone    State = "done"
	StateFailed  State = "failed"
)

// Status tells what the schedule does today and when it starts next.
type Status struct {
	State   State
	Message string
	// Next is the next start; zero if none is planned.
	Next time.Time
}

// today is what happened in today's window.
type today struct {
	date     string
	started  bool // a start was sent; it is never sent again today
	finished bool // nothing more happens today
	waits    int
	state    State
	message  string
}

// Runner checks the schedule every minute, starts the day's tasks once when
// the window opens and sends the robot home once when it closes. Commands
// that move the robot are sent at most once per day.
type Runner struct {
	store *Store
	robot Robot
	tasks Tasks
	saved TaskStore
	cfg   Config
	log   *slog.Logger

	mu        sync.Mutex
	day       today
	listeners []func()
}

// NewRunner returns a runner; Run starts it.
func NewRunner(store *Store, r Robot, t Tasks, saved TaskStore, cfg Config) *Runner {
	if cfg.Now == nil {
		cfg.Now = time.Now
	}
	if cfg.Interval <= 0 {
		cfg.Interval = time.Minute
	}
	if cfg.MaxWaits <= 0 {
		cfg.MaxWaits = 5
	}
	if cfg.Logger == nil {
		cfg.Logger = slog.New(slog.DiscardHandler)
	}
	return &Runner{store: store, robot: r, tasks: t, saved: saved, cfg: cfg, log: cfg.Logger}
}

// Run checks the schedule now and then every Interval until ctx ends.
func (r *Runner) Run(ctx context.Context) {
	t := time.NewTicker(r.cfg.Interval)
	defer t.Stop()
	for {
		r.Check(ctx)
		select {
		case <-ctx.Done():
			return
		case <-t.C:
		}
	}
}

// Check looks at the clock once and starts or ends today's window.
func (r *Runner) Check(ctx context.Context) {
	now := r.cfg.Now()
	sched := r.store.Get()
	d := sched.Days[dayIndex(now)]
	start, end, ok := d.window()
	minute := minuteOfDay(now)

	r.mu.Lock()
	day := r.day
	r.mu.Unlock()
	if date := now.Format(time.DateOnly); day.date != date {
		if day.started && !day.finished { // a window that ended at midnight
			r.end(ctx)
		}
		day = today{date: date}
		r.update(func(t *today) { *t = day })
	}

	switch {
	case !sched.Active || (!ok && !day.started):
		r.update(func(t *today) { t.state, t.message = "", "" })
	case !day.started && !day.finished && minute >= start && minute < end:
		r.start(ctx, d, end)
	case day.started && !day.finished && (!ok || minute >= end):
		r.end(ctx)
	}
}

func (r *Runner) start(ctx context.Context, d Day, end int) {
	snap := r.robot.Snapshot()
	switch snap.Status {
	case robot.StatusIdle, robot.StatusDocked, robot.StatusCharging:
	default:
		r.update(func(t *today) {
			t.waits++
			if t.waits >= r.cfg.MaxWaits {
				t.finished, t.state = true, StateFailed
				t.message = fmt.Sprintf("not started: the robot stayed %s", snap.Status)
				return
			}
			t.state, t.message = StateWaiting, fmt.Sprintf("waiting for the robot (%s)", snap.Status)
		})
		return
	}

	// Marked before sending, so nothing can send it twice.
	r.update(func(t *today) { t.started = true })
	ctx, cancel := context.WithTimeout(ctx, startTimeout)
	defer cancel()
	var err error
	what := "the route on the robot"
	if len(d.TaskIDs) == 0 {
		r.log.Info("schedule: continue the route on the robot")
		err = r.robot.Mow(ctx)
	} else {
		what = fmt.Sprintf("%d tasks", len(d.TaskIDs))
		r.log.Info("schedule: start tasks", "tasks", d.TaskIDs)
		_, err = r.tasks.PlanAndStart(ctx, tasks.Request{TaskIDs: d.TaskIDs})
	}
	if err != nil {
		r.log.Error("schedule: start failed", "err", err)
		r.update(func(t *today) {
			t.finished, t.state, t.message = true, StateFailed, "start failed: "+err.Error()
		})
		return
	}
	r.update(func(t *today) {
		t.state, t.message = StateStarted, fmt.Sprintf("mowing %s until %s", what, clock(end))
	})
}

func (r *Runner) end(ctx context.Context) {
	r.update(func(t *today) { t.finished = true })
	switch st := r.robot.Snapshot().Status; st {
	case robot.StatusMow, robot.StatusTransit:
	default:
		r.update(func(t *today) { t.state, t.message = StateDone, "finished" })
		return
	}
	r.log.Info("schedule: window closed, sending the robot home")
	ctx, cancel := context.WithTimeout(ctx, dockTimeout)
	defer cancel()
	if err := r.robot.DockFor(ctx, robot.DockReasonSchedule); err != nil {
		r.log.Error("schedule: dock failed", "err", err)
		r.update(func(t *today) { t.state, t.message = StateFailed, "sending home failed: "+err.Error() })
		return
	}
	r.update(func(t *today) { t.state, t.message = StateDone, "sent home at the end of the window" })
}

// update changes today's state and tells the listeners if it changed.
func (r *Runner) update(f func(t *today)) {
	r.mu.Lock()
	before := r.day
	f(&r.day)
	changed := r.day != before
	listeners := slices.Clone(r.listeners)
	r.mu.Unlock()
	if changed {
		for _, l := range listeners {
			l()
		}
	}
}

// OnChange registers f to be called when today's state changes.
func (r *Runner) OnChange(f func()) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.listeners = append(r.listeners, f)
}

// Status returns today's state and the next start.
func (r *Runner) Status() Status {
	now := r.cfg.Now()
	sched := r.store.Get()
	r.mu.Lock()
	day := r.day
	r.mu.Unlock()
	if day.date != now.Format(time.DateOnly) {
		day = today{}
	}

	st := Status{State: day.state, Message: day.message}
	if !sched.Active {
		return Status{State: StateOff, Message: "the schedule is off"}
	}
	if st.State == "" {
		st.State = StateOff
		if _, end, ok := sched.Days[dayIndex(now)].window(); ok && minuteOfDay(now) < end {
			st.State = StateWaiting
		}
	}
	st.Next = next(sched, now, day.started || day.finished)
	return st
}

// next is the next start of a window after now; today's only if it has not
// been used.
func next(sched Schedule, now time.Time, todayUsed bool) time.Time {
	for i := range 8 {
		if i == 0 && todayUsed {
			continue
		}
		day := time.Date(now.Year(), now.Month(), now.Day()+i, 0, 0, 0, 0, now.Location())
		start, end, ok := sched.Days[dayIndex(day)].window()
		if !ok {
			continue
		}
		// Wall clock, also on the days the clocks change.
		at := time.Date(day.Year(), day.Month(), day.Day(), start/60, start%60, 0, 0, now.Location())
		if i == 0 {
			if minuteOfDay(now) >= end {
				continue
			}
			if at.Before(now) {
				at = now
			}
		}
		return at
	}
	return time.Time{}
}
