package tasks

import (
	"context"
	"errors"
	"fmt"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// movedM: a robot further than this from where its route was planned would
// drive straight to the start of the route, maybe across an exclusion.
const movedM = 1.0

// Errors of Start; the returned errors wrap them.
var (
	ErrNoPlan    = errors.New("no route planned")
	ErrStalePlan = errors.New("the route no longer fits, calculate it again")
	ErrStarting  = errors.New("mowing is being started already")
)

// Start sends the planned route with its map to the robot and starts mowing.
// Like every command that makes the robot move, it is sent once and never
// repeated; it refuses a route that no longer fits the map or the robot.
func (s *Service) Start(ctx context.Context) error {
	if !s.startMu.TryLock() {
		return ErrStarting
	}
	defer s.startMu.Unlock()

	plan := s.Current()
	if plan == nil {
		return ErrNoPlan
	}
	return s.start(ctx, *plan)
}

// PlanAndStart computes the route for req, like Preview, and starts mowing
// exactly that route, even if someone previews another one meanwhile.
func (s *Service) PlanAndStart(ctx context.Context, req Request) (Plan, error) {
	if !s.startMu.TryLock() {
		return Plan{}, ErrStarting
	}
	defer s.startMu.Unlock()

	plan, err := s.Preview(ctx, req)
	if err != nil {
		return Plan{}, err
	}
	return plan, s.start(ctx, plan)
}

func (s *Service) start(ctx context.Context, plan Plan) error {
	m, err := s.maps.Get(s.maps.ActiveID())
	if err != nil || m.ID != plan.MapID || !m.UpdatedAt.Equal(plan.MapUpdatedAt) {
		return fmt.Errorf("%w: the map changed", ErrStalePlan)
	}
	snap := s.robot.Snapshot()
	if start := startPoint(m, snap.Position, snap.Op == protocol.OpCharge); dist(start, plan.Start) > movedM {
		return fmt.Errorf("%w: the robot moved since", ErrStalePlan)
	}
	if err := s.robot.UploadMap(ctx, m.Robot(plan.Route)); err != nil {
		return fmt.Errorf("send route: %w", err)
	}
	if err := s.robot.Mow(ctx); err != nil {
		return fmt.Errorf("start mowing: %w", err)
	}
	return nil
}
