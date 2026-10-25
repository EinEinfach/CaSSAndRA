package settings

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"net/http"
)

// View is the settings as sent to the browser: passwords are never sent,
// Secrets only tells whether one is set.
type View struct {
	Settings Settings `json:"settings"`
	Secrets  Secrets  `json:"secrets"`
}

// Secrets tells which passwords are set.
type Secrets struct {
	HTTPPassword   bool `json:"httpPassword"`
	MQTTPassword   bool `json:"mqttPassword"`
	APIPassword    bool `json:"apiPassword"`
	BrokerPassword bool `json:"brokerPassword"`
	TelegramToken  bool `json:"telegramToken"`
	PushoverToken  bool `json:"pushoverToken"`
}

// ViewOf returns s without passwords.
func ViewOf(s Settings) View {
	v := View{Settings: s, Secrets: Secrets{
		HTTPPassword:   s.Connection.HTTPPassword != 0,
		MQTTPassword:   s.Connection.MQTTPassword != "",
		APIPassword:    s.API.Password != "",
		BrokerPassword: s.Broker.Password != "",
		TelegramToken:  s.Notify.TelegramToken != "",
		PushoverToken:  s.Notify.PushoverToken != "",
	}}
	v.Settings.Connection.HTTPPassword = 0
	v.Settings.Connection.MQTTPassword = ""
	v.Settings.API.Password = ""
	v.Settings.Broker.Password = ""
	v.Settings.Notify.TelegramToken = ""
	v.Settings.Notify.PushoverToken = ""
	return v
}

// Update is the body of PUT /api/settings. Fields missing in Settings keep
// their value. Passwords in Settings are ignored, so sending a View back
// never clears them; they change only through Passwords (null or missing =
// keep, 0 or "" = remove).
type Update struct {
	Settings  json.RawMessage `json:"settings"`
	Passwords struct {
		HTTPPassword   *int    `json:"httpPassword"`
		MQTTPassword   *string `json:"mqttPassword"`
		APIPassword    *string `json:"apiPassword"`
		BrokerPassword *string `json:"brokerPassword"`
		TelegramToken  *string `json:"telegramToken"`
		PushoverToken  *string `json:"pushoverToken"`
	} `json:"passwords"`
}

const maxBodyBytes = 1 << 16

// Handler serves GET and PUT /api/settings (see Update).
func (s *Store) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/settings", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, ViewOf(s.Get()))
	})
	mux.HandleFunc("PUT /api/settings", func(w http.ResponseWriter, r *http.Request) {
		var u Update
		if !decode(w, http.MaxBytesReader(w, r.Body, maxBodyBytes), &u) {
			return
		}
		// Decode onto the current settings: fields not in the body keep their value.
		cur := s.Get()
		next := cur
		if len(u.Settings) > 0 && !decode(w, bytes.NewReader(u.Settings), &next) {
			return
		}
		next.Connection.HTTPPassword = keep(u.Passwords.HTTPPassword, cur.Connection.HTTPPassword)
		next.Connection.MQTTPassword = keep(u.Passwords.MQTTPassword, cur.Connection.MQTTPassword)
		next.API.Password = keep(u.Passwords.APIPassword, cur.API.Password)
		next.Broker.Password = keep(u.Passwords.BrokerPassword, cur.Broker.Password)
		next.Notify.TelegramToken = keep(u.Passwords.TelegramToken, cur.Notify.TelegramToken)
		next.Notify.PushoverToken = keep(u.Passwords.PushoverToken, cur.Notify.PushoverToken)
		if err := s.Set(next); err != nil {
			status := http.StatusInternalServerError
			if errors.Is(err, ErrInvalid) {
				status = http.StatusBadRequest
			}
			writeError(w, status, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, ViewOf(s.Get()))
	})
	return mux
}

func decode(w http.ResponseWriter, r io.Reader, v any) bool {
	dec := json.NewDecoder(r)
	dec.DisallowUnknownFields()
	if err := dec.Decode(v); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return false
	}
	return true
}

func keep[T any](update *T, cur T) T {
	if update == nil {
		return cur
	}
	return *update
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	var buf bytes.Buffer
	if err := json.NewEncoder(&buf).Encode(body); err != nil {
		http.Error(w, `{"error":"encode response"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = w.Write(buf.Bytes()) // the client is gone if this fails
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
