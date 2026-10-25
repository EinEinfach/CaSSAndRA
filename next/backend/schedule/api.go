package schedule

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

const maxBodyBytes = 1 << 16

// JSON is the response of GET /api/schedule and the "schedule" event.
type JSON struct {
	Schedule Schedule   `json:"schedule"`
	Status   StatusJSON `json:"status"`
}

// StatusJSON is Status in browser format.
type StatusJSON struct {
	State   State  `json:"state"`
	Message string `json:"message"`
	// Next is the next start (RFC 3339, local time); empty if none.
	Next string `json:"next"`
}

// JSON returns the schedule and its status.
func (r *Runner) JSON() JSON {
	st := r.Status()
	next := ""
	if !st.Next.IsZero() {
		next = st.Next.Format(time.RFC3339)
	}
	return JSON{
		Schedule: r.store.Get(),
		Status:   StatusJSON{State: st.State, Message: st.Message, Next: next},
	}
}

// Handler serves GET and PUT /api/schedule.
func (r *Runner) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/schedule", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, r.JSON())
	})
	mux.HandleFunc("PUT /api/schedule", func(w http.ResponseWriter, req *http.Request) {
		var body struct {
			Schedule *Schedule `json:"schedule"`
		}
		dec := json.NewDecoder(http.MaxBytesReader(w, req.Body, maxBodyBytes))
		dec.DisallowUnknownFields()
		if err := dec.Decode(&body); err != nil || body.Schedule == nil {
			writeError(w, http.StatusBadRequest, fmt.Sprintf("invalid JSON body, want {\"schedule\": …}: %v", err))
			return
		}
		if err := r.checkTasks(*body.Schedule); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		if err := r.store.Set(*body.Schedule); err != nil {
			status := http.StatusInternalServerError
			if errors.Is(err, ErrInvalid) {
				status = http.StatusBadRequest
			}
			writeError(w, status, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, r.JSON())
	})
	return mux
}

// checkTasks makes sure every task exists and the tasks of one day belong to
// one map; they are mowed one after another on the active map.
func (r *Runner) checkTasks(s Schedule) error {
	for i, d := range s.Days {
		mapID := ""
		for _, id := range d.TaskIDs {
			t, err := r.saved.Get(id)
			if errors.Is(err, tasks.ErrNotFound) {
				return fmt.Errorf("%w: %s: task %q not found", ErrInvalid, Weekdays[i], id)
			}
			if err != nil {
				return err
			}
			if mapID != "" && t.MapID != mapID {
				return fmt.Errorf("%w: %s: the tasks of one day must belong to one map", ErrInvalid, Weekdays[i])
			}
			mapID = t.MapID
		}
	}
	return nil
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body) // the client is gone if this fails
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
