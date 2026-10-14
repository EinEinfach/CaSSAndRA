package testkit

import (
	"sync"
	"time"
)

// FakeClock is a manually advanced clock. Pass its Now method wherever a
// feature takes a func() time.Time.
type FakeClock struct {
	mu  sync.Mutex
	now time.Time
}

// NewFakeClock returns a clock standing at start.
func NewFakeClock(start time.Time) *FakeClock {
	return &FakeClock{now: start}
}

// Now returns the current fake time.
func (c *FakeClock) Now() time.Time {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.now
}

// Advance moves the clock forward by d.
func (c *FakeClock) Advance(d time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.now = c.now.Add(d)
}
