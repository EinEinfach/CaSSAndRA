package tasks

import (
	"fmt"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
)

// maxNameLen keeps names readable in the UI.
const maxNameLen = 80

// maxParts bounds the planner work of one task.
const maxParts = 20

// Part is one piece of a task: what to mow and how.
type Part struct {
	// Selection is a polygon around the part to mow; empty = the whole garden.
	Selection  []geo.Point `json:"selection"`
	Parameters Parameters  `json:"parameters"`
}

// Validate checks the selection and the parameters.
func (p Part) Validate() error {
	if err := validSelection(p.Selection); err != nil {
		return err
	}
	return p.Parameters.Validate()
}

// Task is a saved mowing job for one map: its parts are mowed one after
// another, each starting where the previous one ended.
type Task struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	MapID     string    `json:"mapId"`
	Parts     []Part    `json:"parts"`
	UpdatedAt time.Time `json:"updatedAt"`
}

// Validate checks that the task can be stored and planned.
func (t Task) Validate() error {
	var errs []string
	name := strings.TrimSpace(t.Name)
	if name == "" || utf8.RuneCountInString(name) > maxNameLen {
		errs = append(errs, fmt.Sprintf("name must have 1 to %d characters", maxNameLen))
	}
	if strings.TrimSpace(t.MapID) == "" {
		errs = append(errs, "mapId must be set")
	}
	if len(t.Parts) == 0 || len(t.Parts) > maxParts {
		errs = append(errs, fmt.Sprintf("a task needs 1 to %d parts", maxParts))
	}
	for i, p := range t.Parts {
		if err := p.Validate(); err != nil {
			errs = append(errs, fmt.Sprintf("part %d: %v", i+1, err))
		}
	}
	if len(errs) > 0 {
		return fmt.Errorf("%w: %s", ErrInvalid, strings.Join(errs, "; "))
	}
	return nil
}

// normalized trims the name and replaces nil lists with empty ones, so the
// JSON never contains null for a list.
func (t Task) normalized() Task {
	t.Name = strings.TrimSpace(t.Name)
	parts := make([]Part, len(t.Parts))
	for i, p := range t.Parts {
		p.Selection = nonNil(p.Selection)
		parts[i] = p
	}
	t.Parts = parts
	return t
}
