package tasks

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
)

// previewTimeout bounds one route computation, including the wait for the
// planner (it computes one route at a time).
const previewTimeout = 2 * time.Minute

const maxBodyBytes = 1 << 20

// PlanJSON is the response of GET /api/tasks/preview and the "plan" event.
type PlanJSON struct {
	Plan *Plan `json:"plan"` // null without a plan
}

// PlanJSON returns the current plan in browser format.
func (s *Service) PlanJSON() PlanJSON {
	return PlanJSON{Plan: s.Current()}
}

// Handler serves the tasks API under /api/tasks/.
func (s *Service) Handler() http.Handler {
	mux := http.NewServeMux()
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
	mux.HandleFunc("DELETE /api/tasks/preview", func(w http.ResponseWriter, _ *http.Request) {
		s.Clear()
		w.WriteHeader(http.StatusNoContent)
	})
	return mux
}

func errorStatus(err error) int {
	switch {
	case errors.Is(err, ErrInvalid), errors.Is(err, ErrNothingToMow), errors.Is(err, planner.ErrInvalid):
		return http.StatusBadRequest
	case errors.Is(err, ErrNoMap):
		return http.StatusConflict
	case errors.Is(err, planner.ErrUnavailable):
		return http.StatusNotImplemented
	case errors.Is(err, context.DeadlineExceeded):
		return http.StatusGatewayTimeout
	default:
		return http.StatusInternalServerError
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
