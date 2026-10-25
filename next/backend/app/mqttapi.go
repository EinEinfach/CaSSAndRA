package app

import (
	"context"
	"log/slog"

	"github.com/EinEinfach/CaSSAndRA/next/backend/mqttapi"
	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

// superviseAPI runs the MQTT API with the current API settings and restarts
// it when they change (signalled on changed), until ctx ends.
func superviseAPI(ctx context.Context, api *mqttapi.API, store *settings.Store, changed <-chan struct{}, log *slog.Logger) {
	for {
		s := store.Get().API
		runCtx, cancel := context.WithCancel(ctx)
		done := make(chan struct{})
		if s.Enabled && s.Broker != "" {
			go func() {
				defer close(done)
				log.Info("mqtt api started", "broker", s.Broker, "prefix", s.ServerName)
				if err := api.Run(runCtx, brokerConfig(s)); err != nil {
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
				again = store.Get().API != s
			}
		}
		log.Info("mqtt api settings changed, restarting")
		cancel()
		<-done
	}
}

func brokerConfig(s settings.API) mqttapi.BrokerConfig {
	return mqttapi.BrokerConfig{
		Broker:   s.Broker,
		ClientID: s.ClientID,
		User:     s.User,
		Password: s.Password,
		Prefix:   s.ServerName,
	}
}
