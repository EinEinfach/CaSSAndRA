// Package server serves the web UI and the HTTP API.
package server

import (
	"encoding/json"
	"errors"
	"io/fs"
	"log/slog"
	"net/http"
	"path"
	"strings"
)

// Options configures the HTTP handler.
type Options struct {
	Version string
	// UI holds the built frontend. index.html is served for every path that
	// is not a file, so client-side routes work on reload.
	UI     fs.FS
	Logger *slog.Logger
}

// Health is the response of GET /api/health.
type Health struct {
	Status  string `json:"status"`
	Version string `json:"version"`
}

// New returns the HTTP handler for the API and the UI.
func New(opts Options) http.Handler {
	if opts.Logger == nil {
		opts.Logger = slog.New(slog.DiscardHandler)
	}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/health", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, opts.Logger, http.StatusOK, Health{Status: "ok", Version: opts.Version})
	})
	mux.HandleFunc("/api/health", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Allow", "GET, HEAD")
		writeJSON(w, opts.Logger, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
	})
	mux.HandleFunc("/api/", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, opts.Logger, http.StatusNotFound, map[string]string{"error": "not found"})
	})
	mux.Handle("/", spa(opts.UI))
	return mux
}

func writeJSON(w http.ResponseWriter, logger *slog.Logger, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(body); err != nil {
		logger.Warn("write json response", "err", err)
	}
}

func spa(ui fs.FS) http.Handler {
	files := http.FileServerFS(ui)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		name := strings.TrimPrefix(path.Clean(r.URL.Path), "/")
		if name != "" {
			if info, err := fs.Stat(ui, name); err == nil && !info.IsDir() {
				files.ServeHTTP(w, r)
				return
			}
		}
		index, err := fs.ReadFile(ui, "index.html")
		if errors.Is(err, fs.ErrNotExist) {
			http.Error(w, "UI not built: run make build", http.StatusNotFound)
			return
		}
		if err != nil {
			http.Error(w, "read index.html", http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write(index)
	})
}
