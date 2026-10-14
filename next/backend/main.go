// Command cassandra runs the CaSSAndRA server.
package main

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"net"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/app"
	"github.com/EinEinfach/CaSSAndRA/next/backend/server"
)

// version is set at build time via -ldflags "-X main.version=...".
var version = "dev"

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}

// envInt reads an integer from the environment, so secrets stay out of the
// process list.
func envInt(name string) (int, error) {
	v := os.Getenv(name)
	if v == "" {
		return 0, nil
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return 0, fmt.Errorf("%s: %w", name, err)
	}
	return n, nil
}

func run() error {
	cfg := app.DefaultConfig()
	httpPassword, err := envInt("CASSANDRA_HTTP_PASSWORD")
	if err != nil {
		return err
	}

	host := flag.String("host", "0.0.0.0", "address to listen on")
	port := flag.Int("port", 8050, "port to listen on")
	logLevel := flag.String("log-level", "info", "debug, info, warn or error")
	showVersion := flag.Bool("version", false, "print version and exit")
	flag.StringVar(&cfg.Link.Kind, "link", app.LinkSim, "connection to the robot: sim, http, uart or mqtt")
	flag.StringVar(&cfg.Link.HTTPURL, "http-url", "", "robot URL for -link http, e.g. http://192.168.1.50")
	flag.IntVar(&cfg.Link.HTTPPassword, "http-password", httpPassword, "robot password for -link http (or CASSANDRA_HTTP_PASSWORD)")
	flag.StringVar(&cfg.Link.UARTPort, "uart-port", "/dev/ttyACM0", "serial port for -link uart")
	flag.IntVar(&cfg.Link.UARTBaud, "uart-baud", 115200, "baud rate for -link uart")
	flag.StringVar(&cfg.Link.MQTT.Broker, "mqtt-broker", "", "broker for -link mqtt, e.g. tcp://192.168.1.10:1883")
	flag.StringVar(&cfg.Link.MQTT.MowerName, "mqtt-mower", "Ardumower", "topic prefix of the robot for -link mqtt")
	flag.StringVar(&cfg.Link.MQTT.ClientID, "mqtt-client-id", "CaSSAndRA", "MQTT client id")
	flag.StringVar(&cfg.Link.MQTT.Username, "mqtt-user", "", "MQTT user")
	flag.StringVar(&cfg.Link.MQTT.Password, "mqtt-password", os.Getenv("CASSANDRA_MQTT_PASSWORD"), "MQTT password (or CASSANDRA_MQTT_PASSWORD)")
	flag.Parse()

	if *showVersion {
		fmt.Println(version)
		return nil
	}
	if cfg.Link.Kind == app.LinkSim {
		cfg.Poll.StateInterval = 200 * time.Millisecond // the simulator is local and cheap
	}

	var level slog.Level
	if err := level.UnmarshalText([]byte(*logLevel)); err != nil {
		return fmt.Errorf("parse log level: %w", err)
	}
	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: level}))

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	ln, err := net.Listen("tcp", net.JoinHostPort(*host, fmt.Sprint(*port)))
	if err != nil {
		return fmt.Errorf("listen: %w", err)
	}
	cfg.Version = version
	cfg.UI = server.EmbeddedUI()
	cfg.Logger = logger
	return app.Run(ctx, cfg, ln)
}
