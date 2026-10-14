// Package app wires all features together and runs CaSSAndRA.
package app

import (
	"context"
	"errors"
	"fmt"
	"io/fs"
	"log/slog"
	"net"
	"net/http"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/server"
)

const shutdownTimeout = 5 * time.Second

// Config holds everything the app needs to start.
type Config struct {
	Version string
	UI      fs.FS
	Logger  *slog.Logger
}

// Run serves CaSSAndRA on ln until ctx is cancelled, then shuts down gracefully.
func Run(ctx context.Context, cfg Config, ln net.Listener) error {
	if cfg.Logger == nil {
		cfg.Logger = slog.New(slog.DiscardHandler)
	}
	srv := &http.Server{
		Handler: server.New(server.Options{
			Version: cfg.Version,
			UI:      cfg.UI,
			Logger:  cfg.Logger,
		}),
		ReadHeaderTimeout: 5 * time.Second,
	}

	serveErr := make(chan error, 1)
	go func() { serveErr <- srv.Serve(ln) }()
	cfg.Logger.Info("CaSSAndRA started", "addr", ln.Addr().String(), "version", cfg.Version)

	select {
	case err := <-serveErr:
		return fmt.Errorf("serve http: %w", err)
	case <-ctx.Done():
	}

	cfg.Logger.Info("shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), shutdownTimeout)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("shutdown http: %w", err)
	}
	if err := <-serveErr; !errors.Is(err, http.ErrServerClosed) {
		return fmt.Errorf("serve http: %w", err)
	}
	return nil
}
