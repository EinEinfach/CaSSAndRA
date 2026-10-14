// Package testkit holds shared fakes and helpers for the tests. Feature code
// must never import it.
package testkit

import (
	"log/slog"
	"strings"
	"testing"
)

// Logger returns a logger that writes to the test log, so output only shows
// up for failing tests or with go test -v.
func Logger(t testing.TB) *slog.Logger {
	t.Helper()
	return slog.New(slog.NewTextHandler(testWriter{t}, &slog.HandlerOptions{Level: slog.LevelDebug}))
}

type testWriter struct{ t testing.TB }

func (w testWriter) Write(p []byte) (int, error) {
	w.t.Log(strings.TrimRight(string(p), "\n"))
	return len(p), nil
}
