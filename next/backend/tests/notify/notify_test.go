package notify_test

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"path/filepath"
	"slices"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/notify"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

const token = "123456:SECRET-TOKEN"

// fakeServices stands in for the Telegram and Pushover APIs.
type fakeServices struct {
	mu       sync.Mutex
	messages []string // "telegram <chat>: text" or "pushover <user>: text"
	chat     int64    // in getUpdates; 0 = no message to the bot
	status   int      // answer of sendMessage / messages.json
	srv      *httptest.Server
}

func newServices(t *testing.T) *fakeServices {
	t.Helper()
	f := &fakeServices{chat: 4242, status: http.StatusOK}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /bot"+token+"/getUpdates", func(w http.ResponseWriter, _ *http.Request) {
		if f.chat == 0 {
			_, _ = io.WriteString(w, `{"ok":true,"result":[]}`)
			return
		}
		_, _ = io.WriteString(w, `{"ok":true,"result":[{"message":{"chat":{"id":1}}},{"message":{"chat":{"id":`+
			strconvI(f.chat)+`}}}]}`)
	})
	mux.HandleFunc("POST /bot"+token+"/sendMessage", func(w http.ResponseWriter, r *http.Request) {
		_ = r.ParseForm()
		f.add("telegram " + r.PostForm.Get("chat_id") + ": " + r.PostForm.Get("text"))
		f.answer(w, `{"ok":false,"description":"Bad Request: chat not found"}`)
	})
	mux.HandleFunc("POST /1/messages.json", func(w http.ResponseWriter, r *http.Request) {
		var body map[string]string
		_ = json.NewDecoder(r.Body).Decode(&body)
		if body["token"] != "pushover-app-token" || body["title"] != "CaSSAndRA" {
			http.Error(w, `{"errors":["application token is invalid"]}`, http.StatusBadRequest)
			return
		}
		f.add("pushover " + body["user"] + ": " + body["message"])
		f.answer(w, `{"status":0,"errors":["user identifier is not active"]}`)
	})
	f.srv = httptest.NewServer(mux)
	t.Cleanup(f.srv.Close)
	return f
}

func strconvI(v int64) string { b, _ := json.Marshal(v); return string(b) }

func (f *fakeServices) add(m string) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.messages = append(f.messages, m)
}

func (f *fakeServices) answer(w http.ResponseWriter, failure string) {
	if f.status != http.StatusOK {
		w.WriteHeader(f.status)
		_, _ = io.WriteString(w, failure)
		return
	}
	_, _ = io.WriteString(w, `{"ok":true,"status":1}`)
}

func (f *fakeServices) sent() []string {
	f.mu.Lock()
	defer f.mu.Unlock()
	return slices.Clone(f.messages)
}

type fakeRobot struct {
	mu   sync.Mutex
	snap robot.Snapshot
}

func (r *fakeRobot) Snapshot() robot.Snapshot {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.snap
}

func (r *fakeRobot) set(st robot.Status, sensor protocol.Sensor) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.snap.Status, r.snap.Sensor = st, sensor
}

func setup(t *testing.T, n settings.Notify) (*notify.Service, *fakeServices, *settings.Store, *fakeRobot) {
	t.Helper()
	f := newServices(t)
	st, err := settings.Open(filepath.Join(t.TempDir(), "settings.json"))
	if err != nil {
		t.Fatal(err)
	}
	s := settings.Default()
	s.Notify = n
	if err := st.Set(s); err != nil {
		t.Fatal(err)
	}
	r := &fakeRobot{}
	svc := notify.New(st, r, notify.Config{TelegramURL: f.srv.URL, PushoverURL: f.srv.URL, Interval: 5 * time.Millisecond})
	return svc, f, st, r
}

var telegram = settings.Notify{Service: settings.NotifyTelegram, TelegramToken: token, TelegramChatID: "77"}

func TestTelegram(t *testing.T) {
	svc, f, _, _ := setup(t, telegram)
	if err := svc.Send(context.Background(), "Hello & good night"); err != nil {
		t.Fatal(err)
	}
	if got := f.sent(); !slices.Equal(got, []string{"telegram 77: Hello & good night"}) {
		t.Errorf("sent %v", got)
	}
}

func TestTelegramFindsAndKeepsTheChat(t *testing.T) {
	n := telegram
	n.TelegramChatID = ""
	svc, f, st, _ := setup(t, n)
	if err := svc.Send(context.Background(), "hi"); err != nil {
		t.Fatal(err)
	}
	if got := f.sent(); !slices.Equal(got, []string{"telegram 4242: hi"}) {
		t.Errorf("sent %v, want to the chat of the latest message", got)
	}
	if got := st.Get().Notify.TelegramChatID; got != "4242" {
		t.Errorf("stored chat id %q", got)
	}

	// Nobody wrote to the bot yet.
	svc2, f2, _, _ := setup(t, n)
	f2.chat = 0
	if err := svc2.Send(context.Background(), "hi"); err == nil || !strings.Contains(err.Error(), "write the bot a message first") {
		t.Errorf("without a chat: %v", err)
	}
}

func TestPushover(t *testing.T) {
	svc, f, _, _ := setup(t, settings.Notify{Service: settings.NotifyPushover, PushoverToken: "pushover-app-token", PushoverUser: "u123"})
	if err := svc.Send(context.Background(), "mowing done"); err != nil {
		t.Fatal(err)
	}
	if got := f.sent(); !slices.Equal(got, []string{"pushover u123: mowing done"}) {
		t.Errorf("sent %v", got)
	}
}

func TestErrorsTellWhyButNeverTheToken(t *testing.T) {
	svc, f, _, _ := setup(t, telegram)
	f.status = http.StatusBadRequest
	err := svc.Send(context.Background(), "hi")
	if err == nil || !strings.Contains(err.Error(), "chat not found") || strings.Contains(err.Error(), "SECRET") {
		t.Errorf("err = %v", err)
	}

	svcDown := notify.New(settingsWith(t, telegram), &fakeRobot{}, notify.Config{TelegramURL: "http://127.0.0.1:1"})
	err = svcDown.Send(context.Background(), "hi")
	if err == nil || strings.Contains(err.Error(), "SECRET") {
		t.Errorf("unreachable: %v", err)
	}
	var ue *url.Error
	if errors.As(err, &ue) {
		t.Error("the error still carries the URL with the token")
	}
}

func settingsWith(t *testing.T, n settings.Notify) *settings.Store {
	t.Helper()
	st, err := settings.Open(filepath.Join(t.TempDir(), "settings.json"))
	if err != nil {
		t.Fatal(err)
	}
	s := settings.Default()
	s.Notify = n
	if err := st.Set(s); err != nil {
		t.Fatal(err)
	}
	return st
}

func TestNothingIsSentWithoutAService(t *testing.T) {
	svc, f, _, _ := setup(t, settings.Notify{})
	if err := svc.Send(context.Background(), "hi"); !errors.Is(err, notify.ErrOff) || len(f.sent()) != 0 {
		t.Errorf("err %v, sent %v", err, f.sent())
	}
}

func TestTheWatcherTellsOfflineAndErrorsOnce(t *testing.T) {
	svc, f, _, r := setup(t, telegram)
	r.set(robot.StatusOffline, 0) // at start: not told
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() { svc.Run(ctx); close(done) }()
	defer func() { cancel(); <-done }()

	steps := []struct {
		status robot.Status
		sensor protocol.Sensor
	}{
		{robot.StatusOffline, 0}, {robot.StatusIdle, 0}, {robot.StatusOffline, 0}, {robot.StatusOffline, 0},
		{robot.StatusMow, 0}, {robot.StatusError, 13}, {robot.StatusError, 13},
	}
	for _, s := range steps {
		r.set(s.status, s.sensor)
		time.Sleep(30 * time.Millisecond)
	}
	want := []string{"telegram 77: Attention! Robot is offline", "telegram 77: Attention! Robot reports an error: bumper"}
	if got := f.sent(); !slices.Equal(got, want) {
		t.Errorf("sent %v, want %v", got, want)
	}
}

func TestTestMessage(t *testing.T) {
	n := telegram
	n.TelegramChatID = ""
	svc, f, _, _ := setup(t, n)
	rec := httptest.NewRecorder()
	svc.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodPost, "/api/notify/test", nil))
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"telegramChatId":"4242"`) {
		t.Errorf("test = %d %s", rec.Code, rec.Body)
	}
	if got := f.sent(); len(got) != 1 || !strings.HasSuffix(got[0], "CaSSAndRA: test message") {
		t.Errorf("sent %v", got)
	}

	off, _, _, _ := setup(t, settings.Notify{})
	rec = httptest.NewRecorder()
	off.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodPost, "/api/notify/test", nil))
	if rec.Code != http.StatusBadRequest {
		t.Errorf("without a service = %d", rec.Code)
	}
}
