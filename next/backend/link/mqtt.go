package link

import (
	"context"
	"fmt"
	"log/slog"
	"strings"
	"sync"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// subscribeTimeout bounds the wait for the broker to confirm a subscription.
const subscribeTimeout = 5 * time.Second

// MQTTConfig describes the broker and the bridge's topic prefix.
type MQTTConfig struct {
	// Broker is the broker URL, e.g. "tcp://192.168.1.10:1883".
	Broker   string
	ClientID string
	Username string
	Password string
	// MowerName is the topic prefix, e.g. "ardumower/Ardumower".
	MowerName      string
	ReconnectDelay time.Duration
	Logger         *slog.Logger
}

// MQTTLink talks to a robot through the MQTT bridge used with legacy
// CaSSAndRA: the bridge publishes JSON on <mower>/state|stats|props and
// "true"/"false" on <mower>/online; commands go to <mower>/command without
// reply.
type MQTTLink struct {
	cfg MQTTConfig
	log *slog.Logger

	mu        sync.Mutex
	client    mqtt.Client
	connected bool // to the broker
}

// NewMQTTLink returns a link for cfg. It connects in Run.
func NewMQTTLink(cfg MQTTConfig) *MQTTLink {
	if cfg.Logger == nil {
		cfg.Logger = slog.New(slog.DiscardHandler)
	}
	if cfg.ReconnectDelay <= 0 {
		cfg.ReconnectDelay = 4 * time.Second
	}
	return &MQTTLink{cfg: cfg, log: cfg.Logger}
}

type mqttMessage struct {
	topic   string
	payload []byte
}

// Run implements Link. Paho delivers messages on its own goroutines; they
// are queued here so the handler is called from Run only, one at a time.
func (l *MQTTLink) Run(ctx context.Context, h Handler) error {
	msgs := make(chan mqttMessage, 256)
	status := make(chan bool, 16)
	prefix := strings.TrimSuffix(l.cfg.MowerName, "/") + "/"

	opts := mqtt.NewClientOptions().
		AddBroker(l.cfg.Broker).
		SetClientID(l.cfg.ClientID).
		SetUsername(l.cfg.Username).
		SetPassword(l.cfg.Password).
		SetAutoReconnect(true).
		SetConnectRetry(true).
		SetConnectRetryInterval(l.cfg.ReconnectDelay).
		SetMaxReconnectInterval(l.cfg.ReconnectDelay).
		SetOnConnectHandler(func(c mqtt.Client) {
			// The session is clean, so subscriptions are renewed on every connect.
			// Report the connection only once the broker confirmed them, or
			// messages sent right after would be lost.
			for _, topic := range []string{"state", "stats", "props", "online"} {
				token := c.Subscribe(prefix+topic, 0, func(_ mqtt.Client, m mqtt.Message) {
					select {
					case msgs <- mqttMessage{m.Topic(), m.Payload()}:
					default:
						l.log.Warn("mqtt message dropped, handler too slow", "topic", m.Topic())
					}
				})
				if !token.WaitTimeout(subscribeTimeout) || token.Error() != nil {
					l.log.Error("mqtt subscribe failed", "topic", prefix+topic, "err", token.Error())
				}
			}
			select {
			case status <- true:
			case <-ctx.Done(): // Run is gone
			}
		}).
		SetConnectionLostHandler(func(_ mqtt.Client, err error) {
			l.log.Warn("mqtt connection lost", "err", err)
			select {
			case status <- false:
			case <-ctx.Done():
			}
		})
	client := mqtt.NewClient(opts)
	l.mu.Lock()
	l.client = client
	l.mu.Unlock()
	client.Connect() // with ConnectRetry it keeps trying in the background

	brokerUp, robotUp, reported := false, true, false
	report := func() {
		if online := brokerUp && robotUp; online != reported {
			reported = online
			h.OnOnline(online)
		}
	}
	for {
		select {
		case <-ctx.Done():
			client.Disconnect(250)
			l.setConnected(false)
			if reported {
				h.OnOnline(false)
			}
			return nil
		case up := <-status:
			brokerUp = up
			l.setConnected(up)
			report()
		case m := <-msgs:
			switch strings.TrimPrefix(m.topic, prefix) {
			case "state":
				if s, err := protocol.ParseBridgeState(m.payload); err == nil {
					h.OnState(s)
				} else {
					l.log.Warn("mqtt state", "err", err)
				}
			case "stats":
				if s, err := protocol.ParseBridgeStats(m.payload); err == nil {
					h.OnStats(s)
				} else {
					l.log.Warn("mqtt stats", "err", err)
				}
			case "props":
				if v, err := protocol.ParseBridgeProps(m.payload); err == nil {
					h.OnVersion(v)
				} else {
					l.log.Warn("mqtt props", "err", err)
				}
			case "online":
				if up, err := protocol.ParseBridgeOnline(m.payload); err == nil {
					robotUp = up
					report()
				} else {
					l.log.Warn("mqtt online", "err", err)
				}
			}
		}
	}
}

// Send implements Link: it publishes payload to <mower>/command. The bridge
// does not reply, so the reply is always "".
func (l *MQTTLink) Send(ctx context.Context, payload string) (string, error) {
	l.mu.Lock()
	client, connected := l.client, l.connected
	l.mu.Unlock()
	if !connected {
		return "", ErrOffline
	}
	topic := strings.TrimSuffix(l.cfg.MowerName, "/") + "/command"
	token := client.Publish(topic, 0, false, payload)
	select {
	case <-ctx.Done():
		return "", ctx.Err()
	case <-token.Done():
	}
	if err := token.Error(); err != nil {
		return "", fmt.Errorf("mqtt publish %s: %w", command(payload), err)
	}
	return "", nil
}

func (l *MQTTLink) setConnected(up bool) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.connected = up
}
