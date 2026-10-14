package server

import (
	"fmt"
	"net/http"
	"sync"
	"time"
)

// clientBuffer is how many events a slow client may lag behind before
// events are dropped for it. Every event carries a full state, so a dropped
// one is replaced by the next.
const clientBuffer = 16

type event struct {
	name string
	data []byte
}

// Hub pushes named events to browsers as Server-Sent Events. New clients
// first receive the latest event of every name, so they start with a
// complete picture.
type Hub struct {
	heartbeat time.Duration

	mu      sync.Mutex
	clients map[chan event]struct{}
	last    map[string][]byte
	order   []string // event names in first-published order
}

// NewHub returns a Hub that sends a keep-alive comment every heartbeat.
func NewHub(heartbeat time.Duration) *Hub {
	return &Hub{
		heartbeat: heartbeat,
		clients:   map[chan event]struct{}{},
		last:      map[string][]byte{},
	}
}

// Publish sends data (one line of JSON) as event name to all clients.
func (h *Hub) Publish(name string, data []byte) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if _, ok := h.last[name]; !ok {
		h.order = append(h.order, name)
	}
	h.last[name] = data
	for c := range h.clients {
		select {
		case c <- event{name, data}:
		default: // client too slow, it gets the next one
		}
	}
}

// Clients returns the number of connected clients.
func (h *Hub) Clients() int {
	h.mu.Lock()
	defer h.mu.Unlock()
	return len(h.clients)
}

// ServeHTTP streams events until the client disconnects.
func (h *Hub) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming not supported", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("X-Accel-Buffering", "no") // nginx: do not buffer

	c := make(chan event, clientBuffer)
	h.mu.Lock()
	initial := make([]event, 0, len(h.order))
	for _, name := range h.order {
		initial = append(initial, event{name, h.last[name]})
	}
	h.clients[c] = struct{}{}
	h.mu.Unlock()
	defer func() {
		h.mu.Lock()
		delete(h.clients, c)
		h.mu.Unlock()
	}()

	for _, e := range initial {
		if writeEvent(w, e) != nil {
			return
		}
	}
	flusher.Flush()

	heartbeat := time.NewTicker(h.heartbeat)
	defer heartbeat.Stop()
	for {
		select {
		case <-r.Context().Done():
			return
		case e := <-c:
			if writeEvent(w, e) != nil {
				return
			}
		case <-heartbeat.C:
			if _, err := fmt.Fprint(w, ": keep-alive\n\n"); err != nil {
				return
			}
		}
		flusher.Flush()
	}
}

func writeEvent(w http.ResponseWriter, e event) error {
	_, err := fmt.Fprintf(w, "event: %s\ndata: %s\n\n", e.name, e.data)
	return err
}
