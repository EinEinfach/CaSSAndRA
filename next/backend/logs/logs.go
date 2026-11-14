// Package logs keeps the latest log records of the app in memory, for the log
// view in the browser (legacy CaSSAndRA showed cassandra.log). It is a
// slog.Handler that passes every record on to the real handler as well.
package logs

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"slices"
	"strconv"
	"strings"
	"sync"
	"time"
)

// DefaultSize is how many records the buffer keeps.
const DefaultSize = 1000

// Entry is one log record as the browser shows it.
type Entry struct {
	Seq     int64     `json:"seq"` // increases by one per record; the browser asks for newer ones
	Time    time.Time `json:"time"`
	Level   string    `json:"level"`   // DEBUG, INFO, WARN, ERROR
	Message string    `json:"message"` // the message with its attributes, key=value
}

// ring is shared by a Buffer and the handlers derived from it.
type ring struct {
	mu      sync.Mutex
	entries []Entry // oldest first, at most size
	size    int
	seq     int64
}

func (r *ring) add(e Entry) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.seq++
	e.Seq = r.seq
	if len(r.entries) == r.size {
		r.entries = slices.Delete(r.entries, 0, 1)
	}
	r.entries = append(r.entries, e)
}

// Buffer is a slog.Handler that keeps the latest records. Safe for concurrent use.
type Buffer struct {
	next   slog.Handler
	ring   *ring
	attrs  string // from WithAttrs, already formatted
	prefix string // from WithGroup, "group." for the keys
}

// NewBuffer keeps the latest size records and passes all on to next.
// Records next does not want (below its level) are not kept either.
func NewBuffer(next slog.Handler, size int) *Buffer {
	if size <= 0 {
		size = DefaultSize
	}
	return &Buffer{next: next, ring: &ring{size: size}}
}

// Enabled implements slog.Handler.
func (b *Buffer) Enabled(ctx context.Context, level slog.Level) bool {
	return b.next.Enabled(ctx, level)
}

// Handle implements slog.Handler.
func (b *Buffer) Handle(ctx context.Context, r slog.Record) error {
	var msg strings.Builder
	msg.WriteString(r.Message)
	msg.WriteString(b.attrs)
	r.Attrs(func(a slog.Attr) bool {
		writeAttr(&msg, b.prefix, a)
		return true
	})
	b.ring.add(Entry{Time: r.Time, Level: r.Level.String(), Message: msg.String()})
	return b.next.Handle(ctx, r)
}

// WithAttrs implements slog.Handler.
func (b *Buffer) WithAttrs(attrs []slog.Attr) slog.Handler {
	var s strings.Builder
	s.WriteString(b.attrs)
	for _, a := range attrs {
		writeAttr(&s, b.prefix, a)
	}
	return &Buffer{next: b.next.WithAttrs(attrs), ring: b.ring, attrs: s.String(), prefix: b.prefix}
}

// WithGroup implements slog.Handler.
func (b *Buffer) WithGroup(name string) slog.Handler {
	if name == "" {
		return b
	}
	return &Buffer{next: b.next.WithGroup(name), ring: b.ring, attrs: b.attrs, prefix: b.prefix + name + "."}
}

func writeAttr(s *strings.Builder, prefix string, a slog.Attr) {
	a.Value = a.Value.Resolve()
	if a.Equal(slog.Attr{}) {
		return
	}
	if a.Value.Kind() == slog.KindGroup {
		p := prefix
		if a.Key != "" {
			p += a.Key + "."
		}
		for _, g := range a.Value.Group() {
			writeAttr(s, p, g)
		}
		return
	}
	v := a.Value.String()
	if v == "" || strings.ContainsAny(v, " =\"") {
		v = strconv.Quote(v)
	}
	fmt.Fprintf(s, " %s%s=%s", prefix, a.Key, v)
}

// Since returns the kept records newer than seq, oldest first; at most limit (0 = all).
func (b *Buffer) Since(seq int64, limit int) []Entry {
	b.ring.mu.Lock()
	defer b.ring.mu.Unlock()
	i, _ := slices.BinarySearchFunc(b.ring.entries, seq+1, func(e Entry, s int64) int {
		return int(e.Seq - s)
	})
	out := slices.Clone(b.ring.entries[i:])
	if limit > 0 && len(out) > limit {
		out = out[len(out)-limit:]
	}
	if out == nil {
		out = []Entry{}
	}
	return out
}

// ListJSON is the response of GET /api/logs.
type ListJSON struct {
	Entries []Entry `json:"entries"`
}

// Handler serves GET /api/logs?after=<seq>: the records after seq (all kept
// ones without it). The browser polls with the last seq it has.
func (b *Buffer) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/logs", func(w http.ResponseWriter, r *http.Request) {
		var after int64
		if s := r.URL.Query().Get("after"); s != "" {
			v, err := strconv.ParseInt(s, 10, 64)
			if err != nil || v < 0 {
				writeJSON(w, http.StatusBadRequest, map[string]string{"error": "after must be a sequence number"})
				return
			}
			after = v
		}
		writeJSON(w, http.StatusOK, ListJSON{Entries: b.Since(after, 0)})
	})
	return mux
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	var buf bytes.Buffer
	if err := json.NewEncoder(&buf).Encode(body); err != nil {
		http.Error(w, `{"error":"encode response"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = w.Write(buf.Bytes()) // the client is gone if this fails
}
