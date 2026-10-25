// Package notify sends short messages to the user with Telegram or
// Pushover: when the robot goes offline or reports an error, and the native
// app's "sendMessage", like legacy CaSSAndRA.
package notify

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

// ErrOff means no message service is chosen.
var ErrOff = errors.New("no message service chosen")

// Robot is what the watcher reads.
type Robot interface {
	Snapshot() robot.Snapshot
}

// Settings gives the current message service and stores a Telegram chat id
// found on the way.
type Settings interface {
	Get() settings.Settings
	Set(s settings.Settings) error
}

// Config holds the injectable parts of a Service.
type Config struct {
	// TelegramURL and PushoverURL are the API roots (tests use their own).
	TelegramURL string
	PushoverURL string
	Client      *http.Client
	// Interval between two looks at the robot (default 5 s, like legacy).
	Interval time.Duration
	Logger   *slog.Logger
}

// Service sends messages and watches the robot.
type Service struct {
	settings Settings
	robot    Robot
	cfg      Config
	log      *slog.Logger

	mu sync.Mutex // one message at a time; protects the chat id lookup
}

// New returns the service; Run starts the watcher.
func New(s Settings, r Robot, cfg Config) *Service {
	if cfg.TelegramURL == "" {
		cfg.TelegramURL = "https://api.telegram.org"
	}
	if cfg.PushoverURL == "" {
		cfg.PushoverURL = "https://api.pushover.net"
	}
	if cfg.Client == nil {
		cfg.Client = &http.Client{Timeout: 15 * time.Second}
	}
	if cfg.Interval <= 0 {
		cfg.Interval = 5 * time.Second
	}
	if cfg.Logger == nil {
		cfg.Logger = slog.New(slog.DiscardHandler)
	}
	return &Service{settings: s, robot: r, cfg: cfg, log: cfg.Logger}
}

// Send sends text with the chosen service.
func (s *Service) Send(ctx context.Context, text string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	n := s.settings.Get().Notify
	switch n.Service {
	case settings.NotifyTelegram:
		return s.telegram(ctx, n, text)
	case settings.NotifyPushover:
		return s.pushover(ctx, n, text)
	}
	return ErrOff
}

func (s *Service) telegram(ctx context.Context, n settings.Notify, text string) error {
	chat := n.TelegramChatID
	if chat == "" {
		found, err := s.telegramChat(ctx, n.TelegramToken)
		if err != nil {
			return err
		}
		chat = found
		all := s.settings.Get()
		all.Notify.TelegramChatID = chat
		if err := s.settings.Set(all); err != nil {
			s.log.Warn("notify: store the telegram chat id", "err", err)
		}
	}
	form := url.Values{"chat_id": {chat}, "text": {text}}
	return s.post(ctx, "telegram", s.cfg.TelegramURL+"/bot"+n.TelegramToken+"/sendMessage",
		"application/x-www-form-urlencoded", strings.NewReader(form.Encode()))
}

// telegramChat finds the chat of the bot's latest message, like legacy:
// the user writes to the bot once.
func (s *Service) telegramChat(ctx context.Context, token string) (string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, s.cfg.TelegramURL+"/bot"+token+"/getUpdates", nil)
	if err != nil {
		return "", errors.New("telegram: invalid token")
	}
	res, err := s.cfg.Client.Do(req)
	if err != nil {
		return "", fmt.Errorf("telegram: %w", withoutURL(err))
	}
	defer func() { _ = res.Body.Close() }()
	var body struct {
		OK     bool `json:"ok"`
		Result []struct {
			Message struct {
				Chat struct {
					ID int64 `json:"id"`
				} `json:"chat"`
			} `json:"message"`
		} `json:"result"`
		Description string `json:"description"`
	}
	if err := json.NewDecoder(io.LimitReader(res.Body, 1<<20)).Decode(&body); err != nil || !body.OK {
		return "", fmt.Errorf("telegram: finding the chat failed (%d %s)", res.StatusCode, body.Description)
	}
	for i := len(body.Result) - 1; i >= 0; i-- {
		if id := body.Result[i].Message.Chat.ID; id != 0 {
			return strconv.FormatInt(id, 10), nil
		}
	}
	return "", errors.New("telegram: no chat found, write the bot a message first")
}

func (s *Service) pushover(ctx context.Context, n settings.Notify, text string) error {
	body, _ := json.Marshal(map[string]string{
		"token": n.PushoverToken, "user": n.PushoverUser, "title": "CaSSAndRA", "message": text,
	})
	return s.post(ctx, "pushover", s.cfg.PushoverURL+"/1/messages.json", "application/json", strings.NewReader(string(body)))
}

// post sends a request; errors never contain the URL, which holds the token.
func (s *Service) post(ctx context.Context, service, target, contentType string, body io.Reader) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, target, body)
	if err != nil {
		return fmt.Errorf("%s: invalid token", service)
	}
	req.Header.Set("Content-Type", contentType)
	res, err := s.cfg.Client.Do(req)
	if err != nil {
		return fmt.Errorf("%s: %w", service, withoutURL(err))
	}
	defer func() { _ = res.Body.Close() }()
	if res.StatusCode/100 != 2 {
		var e struct {
			Description string   `json:"description"` // telegram
			Errors      []string `json:"errors"`      // pushover
		}
		_ = json.NewDecoder(io.LimitReader(res.Body, 1<<16)).Decode(&e)
		reason := strings.TrimSpace(e.Description + " " + strings.Join(e.Errors, ", "))
		return fmt.Errorf("%s: %s %s", service, res.Status, reason)
	}
	return nil
}

func withoutURL(err error) error {
	var ue *url.Error
	if errors.As(err, &ue) {
		return ue.Err
	}
	return err
}

// Run watches the robot until ctx ends: a message when it goes offline or
// reports an error, once until it is fine again (legacy server.py). Nothing
// is sent for the state at start.
func (s *Service) Run(ctx context.Context) {
	t := time.NewTicker(s.cfg.Interval)
	defer t.Stop()
	sent := true
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
		}
		snap := s.robot.Snapshot()
		text := ""
		switch snap.Status {
		case robot.StatusOffline:
			text = "Attention! Robot is offline"
		case robot.StatusError:
			text = "Attention! Robot reports an error: " + snap.Sensor.String()
		default:
			sent = false
			continue
		}
		if sent {
			continue
		}
		sent = true
		if err := s.Send(ctx, text); err != nil && !errors.Is(err, ErrOff) && ctx.Err() == nil {
			s.log.Warn("notify", "err", err)
		}
	}
}

// Handler serves POST /api/notify/test: a test message with the saved
// settings; the answer tells the Telegram chat id found on the way.
func (s *Service) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("POST /api/notify/test", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		err := s.Send(r.Context(), "CaSSAndRA: test message")
		if err != nil {
			status := http.StatusBadGateway
			if errors.Is(err, ErrOff) {
				status = http.StatusBadRequest
			}
			w.WriteHeader(status)
			_ = json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]string{"telegramChatId": s.settings.Get().Notify.TelegramChatID})
	})
	return mux
}
