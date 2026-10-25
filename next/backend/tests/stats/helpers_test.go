package stats_test

import (
	"path/filepath"
	"sync"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/stats"
)

// t0 is a full hour.
var t0 = time.Date(2026, 10, 26, 9, 0, 0, 0, time.UTC)

func open(t *testing.T) (*stats.Store, string) {
	t.Helper()
	path := filepath.Join(t.TempDir(), "stats.db")
	s, err := stats.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = s.Close() })
	return s, path
}

type fakeRobot struct {
	mu   sync.Mutex
	snap robot.Snapshot
}

func (r *fakeRobot) Snapshot() robot.Snapshot {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.snap
}

func (r *fakeRobot) set(f func(s *robot.Snapshot)) {
	r.mu.Lock()
	defer r.mu.Unlock()
	f(&r.snap)
}
