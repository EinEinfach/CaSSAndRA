package schedule

import (
	"errors"
	"fmt"
	"os"
	"slices"
	"sync"

	"github.com/EinEinfach/CaSSAndRA/next/backend/jsonfile"
)

// Store keeps the schedule in one JSON file. Safe for concurrent use.
type Store struct {
	path   string
	exists bool

	mu        sync.Mutex
	sched     Schedule
	listeners []func()
}

// OpenStore loads the schedule from path; a missing file means the default.
func OpenStore(path string) (*Store, error) {
	s := &Store{path: path, sched: Default()}
	var sched Schedule
	err := jsonfile.Read(path, &sched)
	switch {
	case errors.Is(err, os.ErrNotExist):
		return s, nil
	case err != nil:
		return nil, fmt.Errorf("load schedule: %w", err)
	}
	if err := sched.Validate(); err != nil {
		return nil, fmt.Errorf("load schedule: %w", err)
	}
	s.exists, s.sched = true, sched.normalized()
	return s, nil
}

// Exists reports whether the file existed when the store was opened; if
// not, this is the first start and the legacy schedule may be imported.
func (s *Store) Exists() bool { return s.exists }

// Get returns the schedule.
func (s *Store) Get() Schedule {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.copyLocked()
}

func (s *Store) copyLocked() Schedule {
	c := s.sched
	for i := range c.Days {
		c.Days[i].TaskIDs = slices.Clone(c.Days[i].TaskIDs)
	}
	return c
}

// Set validates and stores sched.
func (s *Store) Set(sched Schedule) error {
	if err := sched.Validate(); err != nil {
		return err
	}
	s.mu.Lock()
	err := s.writeLocked(sched.normalized())
	s.mu.Unlock()
	if err == nil {
		s.changed()
	}
	return err
}

// KeepTasks removes the tasks for which keep is false, e.g. deleted ones.
func (s *Store) KeepTasks(keep func(id string) bool) error {
	s.mu.Lock()
	sched, removed := s.copyLocked(), false
	for i := range sched.Days {
		n := len(sched.Days[i].TaskIDs)
		sched.Days[i].TaskIDs = slices.DeleteFunc(sched.Days[i].TaskIDs, func(id string) bool { return !keep(id) })
		removed = removed || len(sched.Days[i].TaskIDs) != n
	}
	var err error
	if removed {
		err = s.writeLocked(sched)
	}
	s.mu.Unlock()
	if removed && err == nil {
		s.changed()
	}
	return err
}

func (s *Store) writeLocked(sched Schedule) error {
	if err := jsonfile.Write(s.path, sched); err != nil {
		return fmt.Errorf("save schedule: %w", err)
	}
	s.sched, s.exists = sched, true
	return nil
}

// OnChange registers f to be called after every change.
func (s *Store) OnChange(f func()) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.listeners = append(s.listeners, f)
}

func (s *Store) changed() {
	s.mu.Lock()
	listeners := slices.Clone(s.listeners)
	s.mu.Unlock()
	for _, f := range listeners {
		f()
	}
}
