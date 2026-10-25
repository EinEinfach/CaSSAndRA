package stats

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"
)

const (
	defaultPoints = 300
	maxPoints     = 2000
	maxRange      = 2 * 366 * 24 * time.Hour
)

// JSON is the response of GET /api/stats.
type JSON struct {
	From    time.Time          `json:"from"`
	To      time.Time          `json:"to"`
	Samples []Sample           `json:"samples"`
	Totals  map[string]float64 `json:"totals"`
}

// Handler serves GET /api/stats?from=…&to=…&points=… (RFC 3339; default:
// the last 24 hours, 300 points).
func (s *Store) Handler(now func() time.Time) http.Handler {
	if now == nil {
		now = time.Now
	}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/stats", func(w http.ResponseWriter, r *http.Request) {
		from, to, points, err := query(r, now())
		if err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		samples, err := s.Samples(r.Context(), from, to, points)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		totals, err := s.Totals(r.Context(), from, to)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, JSON{From: from, To: to, Samples: samples, Totals: totals})
	})
	return mux
}

func query(r *http.Request, now time.Time) (from, to time.Time, points int, err error) {
	q := r.URL.Query()
	to, from, points = now, now.Add(-24*time.Hour), defaultPoints
	parse := func(name string, dst *time.Time) {
		if v := q.Get(name); v != "" && err == nil {
			if *dst, err = time.Parse(time.RFC3339, v); err != nil {
				err = fmt.Errorf("%s: want RFC 3339 like 2026-10-26T00:00:00+01:00", name)
			}
		}
	}
	parse("from", &from)
	parse("to", &to)
	if v := q.Get("points"); v != "" && err == nil {
		if points, err = strconv.Atoi(v); err != nil || points < 1 || points > maxPoints {
			err = fmt.Errorf("points: want 1 to %d", maxPoints)
		}
	}
	if err == nil && (!to.After(from) || to.Sub(from) > maxRange) {
		err = fmt.Errorf("want from before to, at most %d days apart", int(maxRange.Hours()/24))
	}
	return from, to, points, err
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body) // the client is gone if this fails
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
