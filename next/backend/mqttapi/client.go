package mqttapi

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"strings"
	"sync"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
)

// BrokerConfig says where the API publishes.
type BrokerConfig struct {
	// Broker is the broker URL, e.g. "tcp://192.168.1.10:1883".
	Broker   string
	ClientID string // a random suffix is added, like legacy
	User     string
	Password string
	// Prefix is the server name every topic starts with, e.g. "CaSSAndRA".
	Prefix string
	// Interval between two state publications (default 2 s, like legacy;
	// the native app calls a server offline after 20 s without a message).
	Interval       time.Duration
	ReconnectDelay time.Duration
}

const queueSize = 64

// Run connects to the broker and serves the API until ctx ends. Commands
// run one after another, like legacy, so a long one (a route computation)
// delays the next; only stop never waits.
func (a *API) Run(ctx context.Context, bc BrokerConfig) error {
	if bc.Interval <= 0 {
		bc.Interval = 2 * time.Second
	}
	if bc.ReconnectDelay <= 0 {
		bc.ReconnectDelay = 4 * time.Second
	}
	prefix := strings.TrimSuffix(bc.Prefix, "/") + "/"
	queue := make(chan []byte, queueSize)

	opts := mqtt.NewClientOptions().
		AddBroker(bc.Broker).
		SetClientID(bc.ClientID+"-"+randomSuffix()).
		SetUsername(bc.User).
		SetPassword(bc.Password).
		SetWill(prefix+"status", "offline", 0, false).
		SetAutoReconnect(true).
		SetConnectRetry(true).
		SetConnectRetryInterval(bc.ReconnectDelay).
		SetMaxReconnectInterval(bc.ReconnectDelay).
		SetOnConnectHandler(func(c mqtt.Client) {
			a.log.Info("mqtt api connected", "broker", bc.Broker, "prefix", bc.Prefix)
			token := c.Subscribe(prefix+"api_cmd", 0, func(_ mqtt.Client, m mqtt.Message) {
				a.receive(ctx, m.Payload(), queue)
			})
			if !token.WaitTimeout(5*time.Second) || token.Error() != nil {
				a.log.Error("mqtt api subscribe failed", "err", token.Error())
			}
		}).
		SetConnectionLostHandler(func(_ mqtt.Client, err error) {
			a.log.Warn("mqtt api connection lost", "err", err)
		})
	client := mqtt.NewClient(opts)
	client.Connect() // with ConnectRetry it keeps trying in the background

	publish := func(msgs ...Message) {
		if !client.IsConnectionOpen() {
			return
		}
		for _, m := range msgs {
			client.Publish(prefix+m.Topic, 0, false, m.Payload)
		}
	}

	var wg sync.WaitGroup
	defer wg.Wait()
	wg.Go(func() {
		for {
			select {
			case <-ctx.Done():
				return
			case payload := <-queue:
				a.setBusy(true)
				publish(Message{"status", []byte("busy")})
				msgs, err := a.Handle(ctx, payload)
				if err != nil && ctx.Err() == nil {
					a.log.Warn("mqtt api command", "err", err, "payload", truncate(payload))
				}
				publish(msgs...)
				a.setBusy(false)
				publish(Message{"status", []byte("ready")})
			}
		}
	})

	tick := time.NewTicker(bc.Interval)
	defer tick.Stop()
	for {
		select {
		case <-ctx.Done():
			if client.IsConnectionOpen() {
				client.Publish(prefix+"status", 0, false, "offline").WaitTimeout(time.Second)
			}
			client.Disconnect(250)
			return nil
		case <-tick.C:
			publish(a.State()...)
		}
	}
}

// receive queues a command; stop runs at once, before anything queued.
func (a *API) receive(ctx context.Context, payload []byte, queue chan<- []byte) {
	if c, err := parse(payload); err == nil && c.isStop() {
		a.log.Info("mqtt api stop")
		go func() {
			if err := a.robot.Stop(ctx); err != nil && ctx.Err() == nil {
				a.log.Warn("mqtt api stop", "err", err)
			}
		}()
		return
	}
	select {
	case queue <- payload:
	default:
		a.log.Warn("mqtt api command dropped, too many waiting", "payload", truncate(payload))
	}
}

func truncate(b []byte) string {
	if len(b) > 200 {
		return string(b[:200]) + "…"
	}
	return string(b)
}

func randomSuffix() string {
	b := make([]byte, 3)
	_, _ = rand.Read(b) // never fails
	return hex.EncodeToString(b)
}
