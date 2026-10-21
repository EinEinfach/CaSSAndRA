package tasks

import (
	"context"
	"errors"
	"fmt"
	"math"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// ErrUnreachable means the goal lies outside the lawn or cannot be reached.
var ErrUnreachable = errors.New("the robot cannot drive there")

// Goto finds a way from the robot to goal inside the perimeter and around
// the exclusions (A*, preferring the search wire), sends it with the map
// and makes the robot drive it with the mow motor off. Each command is sent
// once. It returns the way.
func (s *Service) Goto(ctx context.Context, goal geo.Point) ([]geo.Point, error) {
	if math.IsNaN(goal.X) || math.IsNaN(goal.Y) || math.IsInf(goal.X, 0) || math.IsInf(goal.Y, 0) {
		return nil, fmt.Errorf("%w: goal is not a point", ErrInvalid)
	}
	if !s.startMu.TryLock() {
		return nil, ErrStarting
	}
	defer s.startMu.Unlock()

	id := s.maps.ActiveID()
	if id == "" {
		return nil, ErrNoMap
	}
	m, err := s.maps.Get(id)
	if err != nil {
		return nil, fmt.Errorf("%w: %w", ErrNoMap, err)
	}
	if !onLawn(m, goal) {
		return nil, fmt.Errorf("%w: the goal lies outside the lawn", ErrUnreachable)
	}
	snap := s.robot.Snapshot()
	start := startPoint(m, snap.Position, snap.Op == protocol.OpCharge)
	way, err := s.planner.Way(ctx, area(m, nil), start, goal)
	if errors.Is(err, planner.ErrNoPath) {
		return nil, fmt.Errorf("%w: %w", ErrUnreachable, err)
	}
	if err != nil {
		return nil, err
	}
	if err := s.robot.UploadMap(ctx, m.Robot(way)); err != nil {
		return nil, fmt.Errorf("send way: %w", err)
	}
	if err := s.robot.Goto(ctx); err != nil {
		return nil, fmt.Errorf("start driving: %w", err)
	}
	return way, nil
}

// onLawn reports whether p lies in the perimeter and in no exclusion.
func onLawn(m maps.Map, p geo.Point) bool {
	if !inside(m.Perimeter, p) {
		return false
	}
	for _, ex := range m.Exclusions {
		if inside(ex, p) && !onBorder(ex, p) {
			return false
		}
	}
	return true
}

func onBorder(polygon []geo.Point, p geo.Point) bool {
	for i, a := range polygon {
		if onSegment(a, polygon[(i+1)%len(polygon)], p) {
			return true
		}
	}
	return false
}
