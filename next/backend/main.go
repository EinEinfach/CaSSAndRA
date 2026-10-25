// Command cassandra runs the CaSSAndRA server.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

	"github.com/EinEinfach/CaSSAndRA/next/backend/app"
	"github.com/EinEinfach/CaSSAndRA/next/backend/server"
	"github.com/EinEinfach/CaSSAndRA/next/backend/system"
)

// version is set at build time via -ldflags "-X main.version=...".
var version = "dev"

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}

func run() error {
	cfg := app.DefaultConfig()
	defaultDataDir := ".cassandra"
	if home, err := os.UserHomeDir(); err == nil {
		defaultDataDir = filepath.Join(home, ".cassandra")
	}

	host := flag.String("host", "0.0.0.0", "address to listen on")
	port := flag.Int("port", 8050, "port to listen on")
	logLevel := flag.String("log-level", "info", "debug, info, warn or error")
	showVersion := flag.Bool("version", false, "print version and exit")
	checkPlanner := flag.Bool("check-planner", false, "compute a route for the demo garden and exit")
	flag.StringVar(&cfg.DataDir, "data-dir", defaultDataDir,
		"directory for settings and maps; legacy CaSSAndRA data there is imported on the first start")
	flag.Parse()

	if *showVersion {
		fmt.Println(version)
		return nil
	}
	if *checkPlanner {
		return app.CheckPlanner(context.Background(), os.Stdout)
	}

	var level slog.Level
	if err := level.UnmarshalText([]byte(*logLevel)); err != nil {
		return fmt.Errorf("parse log level: %w", err)
	}
	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: level}))

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	cfg.Version = version
	cfg.UI = server.EmbeddedUI()
	cfg.Logger = logger
	cfg.PowerOff = system.PowerOff
	// "server restart" over the MQTT API runs the app again in this process,
	// like legacy CaSSAndRA.
	for {
		ln, err := net.Listen("tcp", net.JoinHostPort(*host, fmt.Sprint(*port)))
		if err != nil {
			return fmt.Errorf("listen: %w", err)
		}
		err = app.Run(ctx, cfg, ln)
		if !errors.Is(err, app.ErrRestart) {
			return err
		}
	}
}
