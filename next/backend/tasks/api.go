package tasks

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
)

// startTimeout covers sending a large route over a slow link, the checksum
// wait and the mow command.
const startTimeout = 3 * time.Minute

// previewTimeout bounds one route computation, including the wait for the
// planner (it computes one route at a time).
const previewTimeout = 2 * time.Minute

const maxBodyBytes = 1 << 20

// PlanJSON is the response of GET /api/tasks/preview and the "plan" event.
type PlanJSON struct {
	Plan *Plan `json:"plan"` // null without a plan
}

// GotoJSON is the response of POST /api/tasks/goto.
type GotoJSON struct {
	Way []geo.Point `json:"way"`
}

// ListJSON is the response of GET /api/tasks and the "tasks" event.
type ListJSON struct {
	Tasks []Task `json:"tasks"`
}

// ListJSON returns all saved tasks.
func (s *Service) ListJSON() ListJSON {
	return ListJSON{Tasks: s.tasks.List()}
}

// PlanJSON returns the current plan in browser format.
func (s *Service) PlanJSON() PlanJSON {
	return PlanJSON{Plan: s.Current()}
}

// Handler serves the tasks API under /api/tasks/.
func (s *Service) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/tasks", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, s.ListJSON())
	})
	mux.HandleFunc("POST /api/tasks", func(w http.ResponseWriter, r *http.Request) {
		var t Task
		if !decode(w, r, &t) {
			return
		}
		created, err := s.saveTask(t, true)
		if err != nil {
			writeError(w, errorStatus(err), err.Error())
			return
		}
		writeJSON(w, http.StatusCreated, created)
	})
	mux.HandleFunc("PUT /api/tasks/{id}", func(w http.ResponseWriter, r *http.Request) {
		var t Task
		if !decode(w, r, &t) {
			return
		}
		t.ID = r.PathValue("id")
		updated, err := s.saveTask(t, false)
		if err != nil {
			writeError(w, errorStatus(err), err.Error())
			return
		}
		writeJSON(w, http.StatusOK, updated)
	})
	mux.HandleFunc("DELETE /api/tasks/{id}", func(w http.ResponseWriter, r *http.Request) {
		if err := s.tasks.Delete(r.PathValue("id")); err != nil {
			writeError(w, errorStatus(err), err.Error())
			return
		}
		w.WriteHeader(http.StatusNoContent)
	})
	mux.HandleFunc("GET /api/tasks/preview", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, s.PlanJSON())
	})
	mux.HandleFunc("POST /api/tasks/preview", func(w http.ResponseWriter, r *http.Request) {
		var req Request
		if !decode(w, r, &req) {
			return
		}
		ctx, cancel := context.WithTimeout(r.Context(), previewTimeout)
		defer cancel()
		plan, err := s.Preview(ctx, req)
		if err != nil {
			writeError(w, errorStatus(err), err.Error())
			return
		}
		writeJSON(w, http.StatusOK, plan)
	})
	mux.HandleFunc("POST /api/tasks/start", func(w http.ResponseWriter, r *http.Request) {
		ctx, cancel := context.WithTimeout(r.Context(), startTimeout)
		defer cancel()
		if err := s.Start(ctx); err != nil {
			writeError(w, errorStatus(err), err.Error())
			return
		}
		w.WriteHeader(http.StatusNoContent)
	})
	mux.HandleFunc("POST /api/tasks/goto", func(w http.ResponseWriter, r *http.Request) {
		var goal struct {
			X *float64 `json:"x"`
			Y *float64 `json:"y"`
		}
		if !decode(w, r, &goal) {
			return
		}
		if goal.X == nil || goal.Y == nil {
			writeError(w, http.StatusBadRequest, "missing field x or y")
			return
		}
		ctx, cancel := context.WithTimeout(r.Context(), startTimeout)
		defer cancel()
		way, err := s.Goto(ctx, geo.Point{X: *goal.X, Y: *goal.Y})
		if err != nil {
			writeError(w, errorStatus(err), err.Error())
			return
		}
		writeJSON(w, http.StatusOK, GotoJSON{Way: way})
	})
	mux.HandleFunc("DELETE /api/tasks/preview", func(w http.ResponseWriter, _ *http.Request) {
		s.Clear()
		w.WriteHeader(http.StatusNoContent)
	})
	return mux
}

// saveTask stores t after checking that its map exists.
func (s *Service) saveTask(t Task, create bool) (Task, error) {
	if _, err := s.maps.Get(t.MapID); err != nil {
		return Task{}, fmt.Errorf("%w: unknown map %q", ErrInvalid, t.MapID)
	}
	if create {
		return s.tasks.Create(t)
	}
	return s.tasks.Update(t)
}

func errorStatus(err error) int {
	switch {
	case errors.Is(err, ErrNotFound):
		return http.StatusNotFound
	case errors.Is(err, ErrNameTaken):
		return http.StatusConflict
	case errors.Is(err, ErrInvalid), errors.Is(err, ErrNothingToMow), errors.Is(err, planner.ErrInvalid),
		errors.Is(err, ErrUnreachable):
		return http.StatusBadRequest
	case errors.Is(err, ErrNoMap), errors.Is(err, ErrNoPlan), errors.Is(err, ErrStalePlan), errors.Is(err, ErrStarting):
		return http.StatusConflict
	case errors.Is(err, planner.ErrUnavailable):
		return http.StatusNotImplemented
	case errors.Is(err, planner.ErrFailed):
		return http.StatusInternalServerError
	default:
		return robot.ErrorStatus(err) // offline 503, timeout 504, busy 409, link 502
	}
}

func decode(w http.ResponseWriter, r *http.Request, v any) bool {
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	dec.DisallowUnknownFields()
	if err := dec.Decode(v); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return false
	}
	return true
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	var buf bytes.Buffer
	if err := json.NewEncoder(&buf).Encode(body); err != nil {
		http.Error(w, `{"error":"encode response"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = w.Write(buf.Bytes()) // the client is gone if this fails
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
