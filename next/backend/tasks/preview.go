package tasks

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
)

// Planner computes routes. *planner.Native implements it.
type Planner interface {
	Route(ctx context.Context, area planner.Area, s planner.Settings, start geo.Point) ([]geo.Point, error)
}

// Maps gives the active map. *maps.Store implements it.
type Maps interface {
	ActiveID() string
	Get(id string) (maps.Map, error)
}

// Robot tells where the robot is and mows a route. *robot.Robot implements it.
type Robot interface {
	Snapshot() robot.Snapshot
	UploadMap(ctx context.Context, m protocol.Map) error
	Mow(ctx context.Context) error
}

// Errors besides ErrInvalid; the returned errors wrap them.
var (
	ErrNoMap        = errors.New("no active map")
	ErrNothingToMow = errors.New("the selection leaves nothing to mow")
)

// Request is what the user wants mowed: either parts drawn in the UI or
// saved tasks of the active map, mowed in the given order.
type Request struct {
	Parts   []Part   `json:"parts"`
	TaskIDs []string `json:"taskIds"`
}

// Plan is a computed route for the active map.
type Plan struct {
	MapID string `json:"mapId"`
	// MapUpdatedAt is the version of the map the route was computed for.
	MapUpdatedAt time.Time `json:"mapUpdatedAt"`
	// TaskIDs are the saved tasks the route was planned for, if any.
	TaskIDs   []string    `json:"taskIds"`
	Parts     []Part      `json:"parts"`
	Start     geo.Point   `json:"start"`
	Route     []geo.Point `json:"route"`
	DistanceM float64     `json:"distanceM"`
	CreatedAt time.Time   `json:"createdAt"`
}

// Config holds what the service needs.
type Config struct {
	// Now returns the current time; tests pass a fake clock.
	Now func() time.Time
}

// Service computes previews and keeps the current one.
type Service struct {
	planner Planner
	maps    Maps
	robot   Robot
	tasks   *Store
	now     func() time.Time

	mu        sync.Mutex
	plan      *Plan
	seq       uint64 // number of the latest request
	planSeq   uint64 // request that computed plan
	listeners []func(*Plan)
	// startMu: one start at a time; a second one is refused, not queued.
	startMu sync.Mutex
	// notifyMu keeps notifications in order: the last one sees the latest plan.
	notifyMu sync.Mutex
}

// New returns a service without a plan; saved tasks come from store.
func New(p Planner, m Maps, r Robot, store *Store, cfg Config) *Service {
	if cfg.Now == nil {
		cfg.Now = time.Now
	}
	return &Service{planner: p, maps: m, robot: r, tasks: store, now: cfg.Now}
}

// Preview computes the route for req on the active map, starting where the
// robot is, and makes it the current plan. When previews overlap, the one
// requested last stays, even if it finishes first.
func (s *Service) Preview(ctx context.Context, req Request) (Plan, error) {
	id := s.maps.ActiveID()
	if id == "" {
		return Plan{}, ErrNoMap
	}
	m, err := s.maps.Get(id)
	if err != nil {
		return Plan{}, fmt.Errorf("%w: %w", ErrNoMap, err)
	}
	parts, err := s.parts(req, m.ID)
	if err != nil {
		return Plan{}, err
	}
	snap := s.robot.Snapshot()
	start := startPoint(m, snap.Position, snap.Op == protocol.OpCharge)

	s.mu.Lock()
	s.seq++
	seq := s.seq
	s.mu.Unlock()

	// Each part starts where the previous one ended (legacy calc_task).
	var route []geo.Point
	for i, part := range parts {
		from := start
		if len(route) > 0 {
			from = route[len(route)-1]
		}
		r, err := s.planner.Route(ctx, area(m, part.Selection), part.Parameters.settings(), from)
		if errors.Is(err, planner.ErrInvalid) && len(part.Selection) > 0 {
			return Plan{}, fmt.Errorf("%w (part %d): %w", ErrNothingToMow, i+1, err)
		}
		if err != nil {
			return Plan{}, err
		}
		if len(r) < 2 {
			return Plan{}, fmt.Errorf("%w (part %d)", ErrNothingToMow, i+1)
		}
		if len(route) > 0 {
			route = route[:len(route)-1] // the same point starts the next part
		}
		route = append(route, r...)
	}
	plan := Plan{
		MapID:        m.ID,
		MapUpdatedAt: m.UpdatedAt,
		TaskIDs:      nonNilStrings(req.TaskIDs),
		Parts:        parts,
		Start:        start,
		Route:        route,
		DistanceM:    length(route),
		CreatedAt:    s.now(),
	}

	s.mu.Lock()
	if seq < s.planSeq {
		s.mu.Unlock()
		return plan, nil // a newer preview is already shown
	}
	s.plan, s.planSeq = &plan, seq
	s.mu.Unlock()
	s.changed()
	return plan, nil
}

// parts checks the request and returns the parts to mow, in order.
func (s *Service) parts(req Request, mapID string) ([]Part, error) {
	switch {
	case len(req.Parts) > 0 && len(req.TaskIDs) > 0:
		return nil, fmt.Errorf("%w: give either parts or taskIds", ErrInvalid)
	case len(req.TaskIDs) > 0:
		var parts []Part
		for _, id := range req.TaskIDs {
			t, err := s.tasks.Get(id)
			if err != nil {
				return nil, err
			}
			if t.MapID != mapID {
				return nil, fmt.Errorf("%w: task %q belongs to another map", ErrInvalid, t.Name)
			}
			parts = append(parts, t.Parts...)
		}
		return parts, nil
	case len(req.Parts) > maxParts:
		return nil, fmt.Errorf("%w: at most %d parts", ErrInvalid, maxParts)
	case len(req.Parts) == 0:
		return nil, fmt.Errorf("%w: nothing requested", ErrInvalid)
	}
	parts := make([]Part, len(req.Parts))
	for i, p := range req.Parts {
		if err := p.Validate(); err != nil {
			return nil, fmt.Errorf("part %d: %w", i+1, err)
		}
		p.Selection = nonNil(p.Selection)
		parts[i] = p
	}
	return parts, nil
}

// Current returns the current plan, nil if there is none.
func (s *Service) Current() *Plan {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.plan == nil {
		return nil
	}
	p := *s.plan
	return &p
}

// Clear drops the current plan.
func (s *Service) Clear() {
	s.mu.Lock()
	had := s.plan != nil
	s.plan, s.planSeq = nil, s.seq
	s.mu.Unlock()
	if had {
		s.changed()
	}
}

// MapsChanged drops the plan if the active map changed since it was computed.
// app calls it on every change of the maps.
func (s *Service) MapsChanged() {
	plan := s.Current()
	if plan == nil {
		return
	}
	m, err := s.maps.Get(s.maps.ActiveID())
	if err == nil && m.ID == plan.MapID && m.UpdatedAt.Equal(plan.MapUpdatedAt) {
		return
	}
	s.Clear()
}

// OnChange registers f to be called with the new plan (nil = none) after
// every change. f runs on the caller's goroutine.
func (s *Service) OnChange(f func(*Plan)) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.listeners = append(s.listeners, f)
}

func (s *Service) changed() {
	s.notifyMu.Lock()
	defer s.notifyMu.Unlock()
	plan := s.Current()
	s.mu.Lock()
	listeners := s.listeners
	s.mu.Unlock()
	for _, f := range listeners {
		f(plan)
	}
}

func nonNilStrings(s []string) []string {
	if s == nil {
		return []string{}
	}
	return s
}

func nonNil(p []geo.Point) []geo.Point {
	if p == nil {
		return []geo.Point{}
	}
	return p
}
