package maps

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/jsonfile"
)

// ErrNotFound means there is no map with the given ID.
var ErrNotFound = errors.New("map not found")

// ErrNameTaken means another map already has the name.
var ErrNameTaken = errors.New("map name already taken")

const activeFile = "active.json"

// StoreConfig holds the injectable parts of a Store.
type StoreConfig struct {
	// NewID returns a new unique map ID (default: random hex).
	NewID func() string
	Now   func() time.Time
}

// Store keeps the maps as one JSON file each in a directory, plus the ID
// of the active map. Safe for concurrent use.
type Store struct {
	dir   string
	cfg   StoreConfig
	fresh bool

	mu        sync.Mutex
	maps      map[string]Map
	active    string
	listeners []func()
}

// OpenStore loads all maps from dir and creates dir if needed.
func OpenStore(dir string, cfg StoreConfig) (*Store, error) {
	if cfg.NewID == nil {
		cfg.NewID = randomID
	}
	if cfg.Now == nil {
		cfg.Now = time.Now
	}
	s := &Store{dir: dir, cfg: cfg, maps: map[string]Map{}}
	if _, err := os.Stat(dir); errors.Is(err, os.ErrNotExist) {
		s.fresh = true
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("maps directory: %w", err)
	}
	files, err := filepath.Glob(filepath.Join(dir, "*.json"))
	if err != nil {
		return nil, err
	}
	for _, f := range files {
		if filepath.Base(f) == activeFile {
			continue
		}
		var m Map
		if err := jsonfile.Read(f, &m); err != nil {
			return nil, fmt.Errorf("load map: %w", err)
		}
		if m.ID+".json" != filepath.Base(f) {
			return nil, fmt.Errorf("load map %s: id %q does not match the file name", f, m.ID)
		}
		s.maps[m.ID] = m.normalized()
	}
	var active struct {
		ID string `json:"id"`
	}
	if err := jsonfile.Read(filepath.Join(dir, activeFile), &active); err != nil && !errors.Is(err, os.ErrNotExist) {
		return nil, fmt.Errorf("load active map: %w", err)
	}
	if _, ok := s.maps[active.ID]; ok {
		s.active = active.ID
	}
	return s, nil
}

// Fresh reports whether the directory did not exist before OpenStore, i.e.
// this is the first start.
func (s *Store) Fresh() bool { return s.fresh }

func randomID() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b) // never fails
	return hex.EncodeToString(b)
}

// List returns all maps sorted by name.
func (s *Store) List() []Map {
	s.mu.Lock()
	defer s.mu.Unlock()
	list := make([]Map, 0, len(s.maps))
	for _, m := range s.maps {
		list = append(list, m)
	}
	slices.SortFunc(list, func(a, b Map) int {
		return strings.Compare(strings.ToLower(a.Name), strings.ToLower(b.Name))
	})
	return list
}

// Get returns the map with id.
func (s *Store) Get(id string) (Map, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	m, ok := s.maps[id]
	if !ok {
		return Map{}, fmt.Errorf("%w: %q", ErrNotFound, id)
	}
	return m, nil
}

// Create stores m as a new map with a new ID.
func (s *Store) Create(m Map) (Map, error) {
	return s.save(m, true)
}

// Update replaces the map with m.ID.
func (s *Store) Update(m Map) (Map, error) {
	return s.save(m, false)
}

func (s *Store) save(m Map, create bool) (Map, error) {
	if err := m.Validate(); err != nil {
		return Map{}, err
	}
	m = m.normalized()
	s.mu.Lock()
	if create {
		m.ID = s.cfg.NewID()
	} else if _, ok := s.maps[m.ID]; !ok {
		s.mu.Unlock()
		return Map{}, fmt.Errorf("%w: %q", ErrNotFound, m.ID)
	}
	for id, other := range s.maps {
		if id != m.ID && strings.EqualFold(other.Name, m.Name) {
			s.mu.Unlock()
			return Map{}, fmt.Errorf("%w: %q", ErrNameTaken, m.Name)
		}
	}
	m.UpdatedAt = s.cfg.Now().UTC()
	if err := jsonfile.Write(s.path(m.ID), m); err != nil {
		s.mu.Unlock()
		return Map{}, fmt.Errorf("save map: %w", err)
	}
	s.maps[m.ID] = m
	s.mu.Unlock()
	s.changed()
	return m, nil
}

// Delete removes the map with id. If it was active, no map is active.
func (s *Store) Delete(id string) error {
	s.mu.Lock()
	if _, ok := s.maps[id]; !ok {
		s.mu.Unlock()
		return fmt.Errorf("%w: %q", ErrNotFound, id)
	}
	if s.active == id {
		if err := s.writeActive(""); err != nil {
			s.mu.Unlock()
			return err
		}
		s.active = ""
	}
	if err := os.Remove(s.path(id)); err != nil {
		s.mu.Unlock()
		return fmt.Errorf("delete map: %w", err)
	}
	delete(s.maps, id)
	s.mu.Unlock()
	s.changed()
	return nil
}

// ActiveID returns the ID of the active map, or "" if none is active.
func (s *Store) ActiveID() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.active
}

// SetActive makes the map with id the active one; "" deactivates.
func (s *Store) SetActive(id string) error {
	s.mu.Lock()
	if _, ok := s.maps[id]; !ok && id != "" {
		s.mu.Unlock()
		return fmt.Errorf("%w: %q", ErrNotFound, id)
	}
	if err := s.writeActive(id); err != nil {
		s.mu.Unlock()
		return err
	}
	s.active = id
	s.mu.Unlock()
	s.changed()
	return nil
}

func (s *Store) writeActive(id string) error {
	if err := jsonfile.Write(filepath.Join(s.dir, activeFile), map[string]string{"id": id}); err != nil {
		return fmt.Errorf("save active map: %w", err)
	}
	return nil
}

// OnChange registers f to be called after every change of a map or of the
// active map. f runs on the caller's goroutine.
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

func (s *Store) path(id string) string {
	return filepath.Join(s.dir, id+".json")
}
