package settings

import (
	"errors"
	"fmt"
	"os"
	"sync"

	"github.com/EinEinfach/CaSSAndRA/next/backend/jsonfile"
)

// Store keeps the settings in a JSON file and tells listeners about changes.
// Safe for concurrent use.
type Store struct {
	path string

	setMu     sync.Mutex // serializes Set, so listeners see changes in order
	mu        sync.Mutex
	cur       Settings
	listeners []func(old, next Settings)
}

// Open loads the settings from path. Without a file it starts with Default
// and writes nothing until Set; Exists tells the two cases apart. Fields
// missing in the file (e.g. from an older version) get their defaults.
func Open(path string) (*Store, error) {
	s := Default()
	err := jsonfile.Read(path, &s)
	if err != nil && !errors.Is(err, os.ErrNotExist) {
		return nil, fmt.Errorf("load settings: %w", err)
	}
	if err == nil {
		if err := s.Validate(); err != nil {
			return nil, fmt.Errorf("load settings %s: %w", path, err)
		}
	}
	return &Store{path: path, cur: s}, nil
}

// Exists reports whether the settings file exists.
func (s *Store) Exists() bool {
	_, err := os.Stat(s.path)
	return err == nil
}

// Get returns the current settings.
func (s *Store) Get() Settings {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.cur
}

// Set validates and saves next, then calls the listeners.
func (s *Store) Set(next Settings) error {
	if err := next.Validate(); err != nil {
		return err
	}
	s.setMu.Lock()
	defer s.setMu.Unlock()
	if err := jsonfile.Write(s.path, next); err != nil {
		return fmt.Errorf("save settings: %w", err)
	}
	s.mu.Lock()
	old := s.cur
	s.cur = next
	listeners := s.listeners
	s.mu.Unlock()
	for _, f := range listeners {
		f(old, next)
	}
	return nil
}

// OnChange registers f to be called after every Set with the old and new
// settings. f runs on the caller's goroutine and must not call Set.
func (s *Store) OnChange(f func(old, next Settings)) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.listeners = append(s.listeners, f)
}
