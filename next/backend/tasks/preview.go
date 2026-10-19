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

// Request is what the user wants mowed.
type Request struct {
	// Selection is a polygon around the part to mow; empty = the whole garden.
	Selection  []geo.Point `json:"selection"`
	Parameters Parameters  `json:"parameters"`
}

// Plan is a computed route for the active map.
type Plan struct {
	MapID string `json:"mapId"`
	// MapUpdatedAt is the version of the map the route was computed for.
	MapUpdatedAt time.Time   `json:"mapUpdatedAt"`
	Selection    []geo.Point `json:"selection"`
	Parameters   Parameters  `json:"parameters"`
	Start        geo.Point   `json:"start"`
	Route        []geo.Point `json:"route"`
	DistanceM    float64     `json:"distanceM"`
	CreatedAt    time.Time   `json:"createdAt"`
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

// New returns a service without a plan.
func New(p Planner, m Maps, r Robot, cfg Config) *Service {
	if cfg.Now == nil {
		cfg.Now = time.Now
	}
	return &Service{planner: p, maps: m, robot: r, now: cfg.Now}
}

// Preview computes the route for req on the active map, starting where the
// robot is, and makes it the current plan. When previews overlap, the one
// requested last stays, even if it finishes first.
func (s *Service) Preview(ctx context.Context, req Request) (Plan, error) {
	if err := req.Parameters.Validate(); err != nil {
		return Plan{}, err
	}
	if err := validSelection(req.Selection); err != nil {
		return Plan{}, err
	}
	id := s.maps.ActiveID()
	if id == "" {
		return Plan{}, ErrNoMap
	}
	m, err := s.maps.Get(id)
	if err != nil {
		return Plan{}, fmt.Errorf("%w: %w", ErrNoMap, err)
	}
	snap := s.robot.Snapshot()
	start := startPoint(m, snap.Position, snap.Op == protocol.OpCharge)

	s.mu.Lock()
	s.seq++
	seq := s.seq
	s.mu.Unlock()

	route, err := s.planner.Route(ctx, area(m, req.Selection), req.Parameters.settings(), start)
	if errors.Is(err, planner.ErrInvalid) && len(req.Selection) > 0 {
		return Plan{}, fmt.Errorf("%w: %w", ErrNothingToMow, err)
	}
	if err != nil {
		return Plan{}, err
	}
	if len(route) < 2 {
		return Plan{}, ErrNothingToMow
	}
	plan := Plan{
		MapID:        m.ID,
		MapUpdatedAt: m.UpdatedAt,
		Selection:    nonNil(req.Selection),
		Parameters:   req.Parameters,
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

func nonNil(p []geo.Point) []geo.Point {
	if p == nil {
		return []geo.Point{}
	}
	return p
}
