// Package mqttapi is the MQTT API of legacy CaSSAndRA, kept compatible for
// home automation and the native app (CaSSAndRA_native): state topics under
// <prefix>/ every two seconds, commands as JSON on <prefix>/api_cmd, e.g.
// {"robot": {"command": "mow", "value": ["resume"]}}.
package mqttapi

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
)

// Errors of commands; the returned errors wrap them.
var (
	ErrUnknown = errors.New("unknown command")
	ErrInvalid = errors.New("invalid command value")
)

// commandTimeout bounds one command, including a route computation.
const commandTimeout = 5 * time.Minute

// Message is one MQTT message below the prefix.
type Message struct {
	Topic   string // without prefix, e.g. "robot"
	Payload []byte
}

// Tasks is what the API needs from the tasks feature.
type Tasks interface {
	Goto(ctx context.Context, goal geo.Point) ([]geo.Point, error)
}

// Config holds the injectable parts of the API.
type Config struct {
	// Version is reported on the server topic.
	Version string
	Logger  *slog.Logger
}

// API turns the app's state into the legacy topics and runs the commands.
type API struct {
	robot Robot
	tasks Tasks
	cfg   Config
	log   *slog.Logger

	mu     sync.Mutex
	motion motion
	busy   bool
}

// New returns the API; Run connects it to a broker.
func New(r Robot, t Tasks, cfg Config) *API {
	if cfg.Logger == nil {
		cfg.Logger = slog.New(slog.DiscardHandler)
	}
	return &API{robot: r, tasks: t, cfg: cfg, log: cfg.Logger}
}

// State returns the topics published every two seconds.
func (a *API) State() []Message {
	snap := a.robot.Snapshot()
	a.mu.Lock()
	a.motion.update(snap)
	robotJSON := a.motion.payload(snap)
	status := "ready"
	if a.busy {
		status = "busy"
	}
	a.mu.Unlock()
	return []Message{
		{"status", []byte(status)},
		{"server", mustJSON(a.serverJSON())},
		{"robot", mustJSON(robotJSON)},
	}
}

// ServerJSON is the payload of <prefix>/server.
type ServerJSON struct {
	Software string `json:"software"`
	Version  string `json:"version"`
	CPULoad  *Float `json:"cpuLoad"`
	CPUTemp  *Float `json:"cpuTemp"`
	MemUsage *Float `json:"memUsage"`
	HDDUsage *Float `json:"hddUsage"`
}

func (a *API) serverJSON() ServerJSON {
	return ServerJSON{Software: "CaSSAndRA", Version: a.cfg.Version}
}

func mustJSON(v any) []byte {
	b, err := json.Marshal(v)
	if err != nil {
		panic(fmt.Sprintf("mqttapi: %T cannot be encoded: %v", v, err)) // only our own types
	}
	return b
}

// command is one entry of an api_cmd message.
type command struct {
	Object  string
	Command string          `json:"command"`
	Value   json.RawMessage `json:"value"`
}

// objects are checked in this order, like legacy api.py.
var objects = []string{"tasks", "maps", "robot", "map", "coords", "settings", "server", "schedule"}

func parse(payload []byte) (command, error) {
	var msg map[string]json.RawMessage
	if err := json.Unmarshal(payload, &msg); err != nil {
		return command{}, fmt.Errorf("%w: not a JSON object: %w", ErrInvalid, err)
	}
	for _, o := range objects {
		raw, ok := msg[o]
		if !ok {
			continue
		}
		c := command{Object: o}
		if err := json.Unmarshal(raw, &c); err != nil || c.Command == "" {
			return command{}, fmt.Errorf("%w: %s needs {\"command\": …, \"value\": …}", ErrInvalid, o)
		}
		return c, nil
	}
	return command{}, fmt.Errorf("%w: no known object (%v)", ErrUnknown, objects)
}

// isStop tells commands that must not wait behind others.
func (c command) isStop() bool {
	return c.Object == "robot" && c.Command == "stop"
}

func (c command) numbers(n int) ([]float64, error) {
	var v []float64
	if err := json.Unmarshal(c.Value, &v); err != nil || len(v) < n {
		return nil, fmt.Errorf("%w: %s %s wants %d numbers", ErrInvalid, c.Object, c.Command, n)
	}
	return v, nil
}

func (c command) strings() ([]string, error) {
	var v []string
	if err := json.Unmarshal(c.Value, &v); err != nil {
		return nil, fmt.Errorf("%w: %s %s wants a list of strings", ErrInvalid, c.Object, c.Command)
	}
	return v, nil
}

// points reads {"x": [...], "y": [...]}.
func (c command) points() ([]geo.Point, error) {
	var v struct{ X, Y []float64 }
	if err := json.Unmarshal(c.Value, &v); err != nil || len(v.X) != len(v.Y) {
		return nil, fmt.Errorf("%w: %s %s wants {\"x\": [...], \"y\": [...]}", ErrInvalid, c.Object, c.Command)
	}
	out := make([]geo.Point, len(v.X))
	for i := range v.X {
		out[i] = geo.Point{X: v.X[i], Y: v.Y[i]}
	}
	return out, nil
}

func (c command) point() (geo.Point, error) {
	p, err := c.points()
	if err != nil {
		return geo.Point{}, err
	}
	if len(p) == 0 {
		return geo.Point{}, fmt.Errorf("%w: %s %s wants a point", ErrInvalid, c.Object, c.Command)
	}
	return p[0], nil
}

// Handle runs one api_cmd message and returns the messages it answers with
// (e.g. coordinates). Errors are for the log: legacy answers nothing.
func (a *API) Handle(ctx context.Context, payload []byte) ([]Message, error) {
	c, err := parse(payload)
	if err != nil {
		return nil, err
	}
	ctx, cancel := context.WithTimeout(ctx, commandTimeout)
	defer cancel()
	if c.Object == "robot" {
		return nil, a.robotCommand(ctx, c)
	}
	return nil, fmt.Errorf("%w: %s %s", ErrUnknown, c.Object, c.Command)
}

// mow starts mowing; value[0] says what: resume, task, all or selection.
func (a *API) mow(ctx context.Context, c command) error {
	v, err := c.strings()
	if err != nil || len(v) == 0 {
		return fmt.Errorf("%w: robot mow wants [\"resume\"|\"task\"|\"all\"|\"selection\"]", ErrInvalid)
	}
	if v[0] == "resume" {
		return a.robot.Mow(ctx)
	}
	return fmt.Errorf("%w: robot mow %q", ErrUnknown, v[0])
}

func (a *API) setBusy(b bool) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.busy = b
}
