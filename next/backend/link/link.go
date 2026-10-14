// Package link connects to the robot over HTTP, MQTT, UART or a built-in simulator.
package link

import (
	"context"
	"errors"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// ErrOffline is returned by Send while there is no connection to the robot.
var ErrOffline = errors.New("robot offline")

// Handler receives everything the robot reports. A Link calls it from its Run
// goroutine, one call at a time. Handlers may call Link.Send.
type Handler interface {
	OnOnline(online bool)
	OnVersion(protocol.Version)
	OnState(protocol.State)
	OnStats(protocol.Stats)
	OnObstacles([][]geo.Point)
}

// Link is a connection to the robot.
type Link interface {
	// Run connects, keeps the connection alive and reports to h until ctx
	// ends. It returns nil after ctx is cancelled.
	Run(ctx context.Context, h Handler) error
	// Send transmits one request payload (e.g. "AT+C,...", without checksum)
	// and returns the robot's reply payload. Links without replies (MQTT)
	// return "". Send never retries; callers decide what is safe to repeat.
	Send(ctx context.Context, payload string) (string, error)
}
