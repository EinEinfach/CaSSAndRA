package robot

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"net/http"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// commandTimeout bounds how long an HTTP request waits for the robot.
const commandTimeout = 10 * time.Second

// StateJSON is the robot state as sent to the browser.
type StateJSON struct {
	Status          Status     `json:"status"`
	Online          bool       `json:"online"`
	Firmware        string     `json:"firmware"`
	FirmwareVersion string     `json:"firmwareVersion"`
	Position        geo.Point  `json:"position"`
	HeadingRad      float64    `json:"headingRad"`
	Target          geo.Point  `json:"target"`
	BatteryV        float64    `json:"batteryV"`
	SoCPercent      int        `json:"socPercent"`
	Amps            float64    `json:"amps"`
	Solution        string     `json:"solution"`
	AccuracyM       float64    `json:"accuracyM"`
	Satellites      int        `json:"satellites"`
	Op              string     `json:"op"`
	Sensor          string     `json:"sensor"`
	MowMotorOn      bool       `json:"mowMotorOn"`
	MowPointIndex   int        `json:"mowPointIndex"`
	DockReason      DockReason `json:"dockReason"`
	MapCRC          int64      `json:"mapCrc"`
	UpdatedAt       *time.Time `json:"updatedAt"`
}

// MapJSON is the map last uploaded to the robot.
type MapJSON struct {
	Perimeter  []geo.Point   `json:"perimeter"`
	Exclusions [][]geo.Point `json:"exclusions"`
	Dock       []geo.Point   `json:"dock"`
	Way        []geo.Point   `json:"way"`
}

// StateJSON returns the current state in browser format.
func (r *Robot) StateJSON() StateJSON {
	s := r.Snapshot()
	var updated *time.Time
	if !s.UpdatedAt.IsZero() {
		updated = &s.UpdatedAt
	}
	return StateJSON{
		Status: s.Status, Online: s.Online, Firmware: s.Firmware, FirmwareVersion: s.FirmwareVersion,
		Position: s.Position, HeadingRad: finite(s.HeadingRad), Target: s.Target,
		BatteryV: finite(s.BatteryV), SoCPercent: s.SoCPercent, Amps: finite(s.Amps),
		Solution: s.Solution.String(), AccuracyM: finite(s.AccuracyM), Satellites: s.Satellites,
		Op: s.Op.String(), Sensor: s.Sensor.String(), MowMotorOn: s.MowMotorOn,
		MowPointIndex: s.MowPointIndex, DockReason: s.DockReason, MapCRC: s.MapCRC, UpdatedAt: updated,
	}
}

// MapJSON returns the last uploaded map in browser format. Lists are never
// null, so the browser does not need to check.
func (r *Robot) MapJSON() MapJSON {
	m := r.Map()
	nonNil := func(p []geo.Point) []geo.Point {
		if p == nil {
			return []geo.Point{}
		}
		return p
	}
	ex := make([][]geo.Point, len(m.Exclusions))
	for i, e := range m.Exclusions {
		ex[i] = nonNil(e)
	}
	return MapJSON{Perimeter: nonNil(m.Perimeter), Exclusions: ex, Dock: nonNil(m.Dock), Way: nonNil(m.Way)}
}

// finite replaces NaN/Inf (e.g. GPS accuracy without fix), which JSON cannot encode.
func finite(v float64) float64 {
	if math.IsNaN(v) || math.IsInf(v, 0) {
		return 0
	}
	return v
}

// PublishState calls publish with the JSON state every interval if it changed,
// until ctx ends. Time-based changes (e.g. going offline) are picked up too.
func (r *Robot) PublishState(ctx context.Context, every time.Duration, publish func([]byte)) {
	t := time.NewTicker(every)
	defer t.Stop()
	var last []byte
	for {
		data, err := json.Marshal(r.StateJSON())
		if err != nil {
			r.log.Error("encode robot state", "err", err)
		} else if !bytes.Equal(data, last) {
			publish(data)
			last = data
		}
		select {
		case <-ctx.Done():
			return
		case <-t.C:
		}
	}
}

// Handler serves the robot API under /api/robot/.
func (r *Robot) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/robot/state", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, r.StateJSON())
	})
	mux.HandleFunc("GET /api/robot/map", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, r.MapJSON())
	})

	simple := map[string]func(context.Context) error{
		"stop":            r.Stop,
		"dock":            r.Dock,
		"mow":             r.Mow,
		"goto":            r.Goto,
		"skip-next-point": r.SkipNextPoint,
		"reboot":          r.Reboot,
		"reboot-gps":      r.RebootGPS,
		"shutdown":        r.Shutdown,
	}
	for name, cmd := range simple {
		mux.HandleFunc("POST /api/robot/"+name, func(w http.ResponseWriter, req *http.Request) {
			run(w, req, cmd)
		})
	}

	mux.HandleFunc("POST /api/robot/move", func(w http.ResponseWriter, req *http.Request) {
		var body struct {
			Linear  *float64 `json:"linear"`
			Angular *float64 `json:"angular"`
		}
		if !decode(w, req, &body) || !required(w, body.Linear, body.Angular) {
			return
		}
		if !inRange(w, "linear", *body.Linear, 1) || !inRange(w, "angular", *body.Angular, 2) {
			return
		}
		run(w, req, func(ctx context.Context) error { return r.Move(ctx, *body.Linear, *body.Angular) })
	})
	mux.HandleFunc("POST /api/robot/mow-motor", func(w http.ResponseWriter, req *http.Request) {
		var body struct {
			On *bool `json:"on"`
		}
		if !decode(w, req, &body) || !required(w, body.On) {
			return
		}
		run(w, req, func(ctx context.Context) error { return r.SetMowMotor(ctx, *body.On) })
	})
	mux.HandleFunc("POST /api/robot/speed", func(w http.ResponseWriter, req *http.Request) {
		var body struct {
			Mps *float64 `json:"mps"`
		}
		if !decode(w, req, &body) || !required(w, body.Mps) || !inRange(w, "mps", *body.Mps, 1) {
			return
		}
		if *body.Mps < 0 {
			writeError(w, http.StatusBadRequest, "mps must not be negative")
			return
		}
		run(w, req, func(ctx context.Context) error { return r.SetSpeed(ctx, *body.Mps) })
	})
	mux.HandleFunc("POST /api/robot/skip-to-progress", func(w http.ResponseWriter, req *http.Request) {
		var body struct {
			Fraction *float64 `json:"fraction"`
		}
		if !decode(w, req, &body) || !required(w, body.Fraction) {
			return
		}
		if f := *body.Fraction; f < 0 || f > 1 {
			writeError(w, http.StatusBadRequest, "fraction must be between 0 and 1")
			return
		}
		run(w, req, func(ctx context.Context) error { return r.SkipToProgress(ctx, *body.Fraction) })
	})
	return mux
}

// run executes a command and maps its error to an HTTP status.
func run(w http.ResponseWriter, req *http.Request, cmd func(context.Context) error) {
	ctx, cancel := context.WithTimeout(req.Context(), commandTimeout)
	defer cancel()
	err := cmd(ctx)
	switch {
	case err == nil:
		w.WriteHeader(http.StatusNoContent)
	case errors.Is(err, link.ErrOffline):
		writeError(w, http.StatusServiceUnavailable, err.Error())
	case errors.Is(err, context.DeadlineExceeded):
		writeError(w, http.StatusGatewayTimeout, err.Error())
	default:
		writeError(w, http.StatusBadGateway, err.Error())
	}
}

const maxBodyBytes = 1 << 16

func decode(w http.ResponseWriter, req *http.Request, v any) bool {
	dec := json.NewDecoder(http.MaxBytesReader(w, req.Body, maxBodyBytes))
	dec.DisallowUnknownFields()
	if err := dec.Decode(v); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return false
	}
	return true
}

func required[T any](w http.ResponseWriter, fields ...*T) bool {
	for _, f := range fields {
		if f == nil {
			writeError(w, http.StatusBadRequest, "missing field")
			return false
		}
	}
	return true
}

func inRange(w http.ResponseWriter, name string, v, limit float64) bool {
	if math.IsNaN(v) || math.Abs(v) > limit {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("%s must be between -%g and %g", name, limit, limit))
		return false
	}
	return true
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body) // the client is gone if this fails
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// Map returns the map last uploaded with UploadMap.
func (r *Robot) Map() protocol.Map {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.uploaded
}
