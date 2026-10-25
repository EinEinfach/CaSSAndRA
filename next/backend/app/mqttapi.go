package app

import (
	"context"
	"log/slog"
	"net"
	"strconv"

	"github.com/EinEinfach/CaSSAndRA/next/backend/mqttapi"
	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

// superviseAPI runs the MQTT API with the current API settings and restarts
// it when they change (signalled on changed), until ctx ends.
func superviseAPI(ctx context.Context, api *mqttapi.API, store *settings.Store, changed <-chan struct{}, log *slog.Logger) {
	for {
		all := store.Get()
		s := all.API
		runCtx, cancel := context.WithCancel(ctx)
		done := make(chan struct{})
		if s.Enabled && (s.Broker != "" || s.UseBuiltinBroker) {
			bc := brokerConfig(all)
			go func() {
				defer close(done)
				log.Info("mqtt api started", "broker", bc.Broker, "prefix", s.ServerName)
				if err := api.Run(runCtx, bc); err != nil {
					log.Error("mqtt api stopped", "err", err)
				}
			}()
		} else {
			close(done)
		}
		for again := false; !again; {
			select {
			case <-ctx.Done():
				cancel()
				<-done
				return
			case <-changed:
				next := store.Get()
				again = next.API != s || (s.UseBuiltinBroker && next.Broker != all.Broker)
			}
		}
		log.Info("mqtt api settings changed, restarting")
		cancel()
		<-done
	}
}

// brokerConfig is the broker the API publishes to: the configured one or
// the built-in one on this computer.
func brokerConfig(all settings.Settings) mqttapi.BrokerConfig {
	s := all.API
	bc := mqttapi.BrokerConfig{
		Broker:   s.Broker,
		ClientID: s.ClientID,
		User:     s.User,
		Password: s.Password,
		Prefix:   s.ServerName,
	}
	if s.UseBuiltinBroker {
		b := all.Broker
		bc.Broker = "tcp://" + net.JoinHostPort("127.0.0.1", strconv.Itoa(b.Port))
		bc.User, bc.Password = b.User, b.Password
	}
	return bc
}
