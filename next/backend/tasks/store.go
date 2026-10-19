package tasks

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"slices"
	"strings"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/jsonfile"
)

// Errors of the store; the returned errors wrap them.
var (
	ErrNotFound  = errors.New("task not found")
	ErrNameTaken = errors.New("task name already taken for this map")
)

// StoreConfig holds the injectable parts of a Store.
type StoreConfig struct {
	// NewID returns a new unique task ID (default: random hex).
	NewID func() string
	Now   func() time.Time
}

// file is the content of tasks.json.
type file struct {
	Tasks []Task `json:"tasks"`
}

// Store keeps all tasks in one JSON file. Safe for concurrent use.
type Store struct {
	path   string
	cfg    StoreConfig
	exists bool

	mu        sync.Mutex
	tasks     map[string]Task
	listeners []func()
}

// OpenStore loads the tasks from path; a missing file means no tasks.
func OpenStore(path string, cfg StoreConfig) (*Store, error) {
	if cfg.NewID == nil {
		cfg.NewID = randomID
	}
	if cfg.Now == nil {
		cfg.Now = time.Now
	}
	s := &Store{path: path, cfg: cfg, tasks: map[string]Task{}}
	var f file
	err := jsonfile.Read(path, &f)
	switch {
	case errors.Is(err, os.ErrNotExist):
		return s, nil
	case err != nil:
		return nil, fmt.Errorf("load tasks: %w", err)
	}
	s.exists = true
	for _, t := range f.Tasks {
		if t.ID == "" || s.tasks[t.ID].ID != "" {
			return nil, fmt.Errorf("load tasks: missing or duplicate id %q", t.ID)
		}
		s.tasks[t.ID] = t.normalized()
	}
	return s, nil
}

// Exists reports whether the file existed when the store was opened; if
// not, this is the first start and legacy tasks may be imported.
func (s *Store) Exists() bool { return s.exists }

func randomID() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b) // never fails
	return hex.EncodeToString(b)
}

// List returns all tasks sorted by map and name.
func (s *Store) List() []Task {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.listLocked()
}

func (s *Store) listLocked() []Task {
	list := make([]Task, 0, len(s.tasks))
	for _, t := range s.tasks {
		list = append(list, t)
	}
	slices.SortFunc(list, func(a, b Task) int {
		if c := strings.Compare(a.MapID, b.MapID); c != 0 {
			return c
		}
		return strings.Compare(strings.ToLower(a.Name), strings.ToLower(b.Name))
	})
	return list
}

// Get returns the task with id.
func (s *Store) Get(id string) (Task, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	t, ok := s.tasks[id]
	if !ok {
		return Task{}, fmt.Errorf("%w: %q", ErrNotFound, id)
	}
	return t, nil
}

// Create stores t as a new task with a new ID.
func (s *Store) Create(t Task) (Task, error) {
	return s.save(t, true)
}

// Update replaces the task with t.ID.
func (s *Store) Update(t Task) (Task, error) {
	return s.save(t, false)
}

func (s *Store) save(t Task, create bool) (Task, error) {
	if err := t.Validate(); err != nil {
		return Task{}, err
	}
	t = t.normalized()
	s.mu.Lock()
	if create {
		t.ID = s.cfg.NewID()
	} else if _, ok := s.tasks[t.ID]; !ok {
		s.mu.Unlock()
		return Task{}, fmt.Errorf("%w: %q", ErrNotFound, t.ID)
	}
	for id, other := range s.tasks {
		if id != t.ID && other.MapID == t.MapID && strings.EqualFold(other.Name, t.Name) {
			s.mu.Unlock()
			return Task{}, fmt.Errorf("%w: %q", ErrNameTaken, t.Name)
		}
	}
	t.UpdatedAt = s.cfg.Now().UTC()
	old, had := s.tasks[t.ID]
	s.tasks[t.ID] = t
	if err := s.writeLocked(); err != nil {
		if had {
			s.tasks[t.ID] = old
		} else {
			delete(s.tasks, t.ID)
		}
		s.mu.Unlock()
		return Task{}, err
	}
	s.mu.Unlock()
	s.changed()
	return t, nil
}

// Delete removes the task with id.
func (s *Store) Delete(id string) error {
	s.mu.Lock()
	old, ok := s.tasks[id]
	if !ok {
		s.mu.Unlock()
		return fmt.Errorf("%w: %q", ErrNotFound, id)
	}
	delete(s.tasks, id)
	if err := s.writeLocked(); err != nil {
		s.tasks[id] = old
		s.mu.Unlock()
		return err
	}
	s.mu.Unlock()
	s.changed()
	return nil
}

// KeepMaps removes the tasks of maps that no longer exist (keep reports
// false). app calls it after every change of the maps.
func (s *Store) KeepMaps(keep func(mapID string) bool) error {
	s.mu.Lock()
	removed := map[string]Task{}
	for id, t := range s.tasks {
		if !keep(t.MapID) {
			removed[id] = t
			delete(s.tasks, id)
		}
	}
	if len(removed) == 0 {
		s.mu.Unlock()
		return nil
	}
	if err := s.writeLocked(); err != nil {
		for id, t := range removed {
			s.tasks[id] = t
		}
		s.mu.Unlock()
		return err
	}
	s.mu.Unlock()
	s.changed()
	return nil
}

func (s *Store) writeLocked() error {
	if err := jsonfile.Write(s.path, file{Tasks: s.listLocked()}); err != nil {
		return fmt.Errorf("save tasks: %w", err)
	}
	s.exists = true
	return nil
}

// OnChange registers f to be called after every change. f runs on the
// caller's goroutine.
func (s *Store) OnChange(f func()) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.listeners = append(s.listeners, f)
}

func (s *Store) changed() {
	s.mu.Lock()
	listeners := s.listeners
	s.mu.Unlock()
	for _, f := range listeners {
		f()
	}
}
