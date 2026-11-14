package maps

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
)

// Uploader transfers a map to the robot. *robot.Robot implements it.
type Uploader interface {
	UploadMap(ctx context.Context, m protocol.Map) error
}

// Reshaper adds an area to a lawn or cuts it out. *planner.Native implements it.
type Reshaper interface {
	Reshape(area planner.Area, figure []geo.Point, add bool) (perimeter []geo.Point, exclusions [][]geo.Point, err error)
}

// ReshapeJSON is the body of POST /api/maps/reshape: the lawn being edited
// (not a saved map), the drawn area and what to do with it.
type ReshapeJSON struct {
	Perimeter  []geo.Point   `json:"perimeter"`
	Exclusions [][]geo.Point `json:"exclusions"`
	Figure     []geo.Point   `json:"figure"`
	Op         string        `json:"op"` // "add" or "subtract"
}

// LawnJSON is the reshaped lawn.
type LawnJSON struct {
	Perimeter  []geo.Point   `json:"perimeter"`
	Exclusions [][]geo.Point `json:"exclusions"`
}

// uploadTimeout covers large maps over slow links plus the checksum wait.
const uploadTimeout = 2 * time.Minute

const maxBodyBytes = 4 << 20 // a few thousand points

// ListJSON is the response of GET /api/maps and the "maps" event.
type ListJSON struct {
	ActiveID string `json:"activeId"`
	Maps     []Map  `json:"maps"`
}

// ListJSON returns all maps and the active one.
func (s *Store) ListJSON() ListJSON {
	return ListJSON{ActiveID: s.ActiveID(), Maps: s.List()}
}

// Handler serves the maps API under /api/maps.
func (s *Store) Handler(up Uploader, shaper Reshaper) http.Handler {
	mux := http.NewServeMux()
	// Stateless: the editor in the browser keeps the draft and its undo history.
	mux.HandleFunc("POST /api/maps/reshape", func(w http.ResponseWriter, r *http.Request) {
		var body ReshapeJSON
		if !decode(w, r, &body) {
			return
		}
		if body.Op != "add" && body.Op != "subtract" {
			writeError(w, http.StatusBadRequest, `op must be "add" or "subtract"`)
			return
		}
		area := planner.Area{Perimeter: body.Perimeter, Exclusions: body.Exclusions}
		perimeter, exclusions, err := shaper.Reshape(area, body.Figure, body.Op == "add")
		switch {
		case errors.Is(err, planner.ErrInvalid):
			writeError(w, http.StatusBadRequest, err.Error())
		case errors.Is(err, planner.ErrUnavailable):
			writeError(w, http.StatusNotImplemented, err.Error())
		case err != nil:
			writeError(w, http.StatusInternalServerError, err.Error())
		default:
			if exclusions == nil {
				exclusions = [][]geo.Point{}
			}
			writeJSON(w, http.StatusOK, LawnJSON{Perimeter: perimeter, Exclusions: exclusions})
		}
	})
	mux.HandleFunc("GET /api/maps", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, s.ListJSON())
	})
	mux.HandleFunc("POST /api/maps", func(w http.ResponseWriter, r *http.Request) {
		var m Map
		if !decode(w, r, &m) {
			return
		}
		created, err := s.Create(m)
		if err != nil {
			writeError(w, storeStatus(err), err.Error())
			return
		}
		writeJSON(w, http.StatusCreated, created)
	})
	mux.HandleFunc("PUT /api/maps/active", func(w http.ResponseWriter, r *http.Request) {
		var body struct {
			ID *string `json:"id"`
		}
		if !decode(w, r, &body) {
			return
		}
		if body.ID == nil {
			writeError(w, http.StatusBadRequest, "missing field id (\"\" deactivates)")
			return
		}
		if err := s.SetActive(*body.ID); err != nil {
			writeError(w, storeStatus(err), err.Error())
			return
		}
		w.WriteHeader(http.StatusNoContent)
	})
	mux.HandleFunc("GET /api/maps/{id}", func(w http.ResponseWriter, r *http.Request) {
		m, err := s.Get(r.PathValue("id"))
		if err != nil {
			writeError(w, storeStatus(err), err.Error())
			return
		}
		writeJSON(w, http.StatusOK, m)
	})
	mux.HandleFunc("PUT /api/maps/{id}", func(w http.ResponseWriter, r *http.Request) {
		var m Map
		if !decode(w, r, &m) {
			return
		}
		m.ID = r.PathValue("id")
		updated, err := s.Update(m)
		if err != nil {
			writeError(w, storeStatus(err), err.Error())
			return
		}
		writeJSON(w, http.StatusOK, updated)
	})
	mux.HandleFunc("DELETE /api/maps/{id}", func(w http.ResponseWriter, r *http.Request) {
		if err := s.Delete(r.PathValue("id")); err != nil {
			writeError(w, storeStatus(err), err.Error())
			return
		}
		w.WriteHeader(http.StatusNoContent)
	})
	mux.HandleFunc("POST /api/maps/{id}/upload", func(w http.ResponseWriter, r *http.Request) {
		m, err := s.Get(r.PathValue("id"))
		if err != nil {
			writeError(w, storeStatus(err), err.Error())
			return
		}
		ctx, cancel := context.WithTimeout(r.Context(), uploadTimeout)
		defer cancel()
		if err := up.UploadMap(ctx, m.Robot(nil)); err != nil {
			writeError(w, robot.ErrorStatus(err), err.Error())
			return
		}
		if err := s.SetActive(m.ID); err != nil {
			writeError(w, storeStatus(err), err.Error())
			return
		}
		w.WriteHeader(http.StatusNoContent)
	})
	return mux
}

func storeStatus(err error) int {
	switch {
	case errors.Is(err, ErrNotFound):
		return http.StatusNotFound
	case errors.Is(err, ErrInvalid):
		return http.StatusBadRequest
	case errors.Is(err, ErrNameTaken):
		return http.StatusConflict
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
