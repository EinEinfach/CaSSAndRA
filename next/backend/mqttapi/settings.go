package mqttapi

import (
	"encoding/json"
	"fmt"
	"net"
	"net/url"
	"strconv"
	"strings"

	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

// Settings is what the API needs from the settings store.
type Settings interface {
	Get() settings.Settings
	Set(s settings.Settings) error
}

// SettingsJSON is the payload of <prefix>/settings, sent on "settings
// update" (legacy settingstopic.py). Passwords and tokens are always empty:
// legacy sent them in plain text to everyone on the broker. An empty
// password in setComm keeps the stored one.
type SettingsJSON struct {
	RobotConnectionType        string  `json:"robotConnectionType"`
	HTTPRobotIPAdress          string  `json:"httpRobotIpAdress"`
	HTTPRobotPassword          string  `json:"httpRobotPassword"`
	MQTTClientID               string  `json:"mqttClientId"`
	MQTTUser                   string  `json:"mqttUser"`
	MQTTPassword               string  `json:"mqttPassword"`
	MQTTServer                 string  `json:"mqttServer"`
	MQTTPort                   int     `json:"mqttPort"`
	MQTTMowerNameWithPrefix    string  `json:"mqttMowerNameWithPrefix"`
	UARTPort                   string  `json:"uartPort"`
	UARTBaudrate               int     `json:"uartBaudrate"`
	APIType                    *string `json:"apiType"`
	APIMQTTClientID            string  `json:"apiMqttClientId"`
	APIMQTTUser                string  `json:"apiMqttUser"`
	APIMQTTPassword            string  `json:"apiMqttPassword"`
	APIMQTTServer              string  `json:"apiMqttServer"`
	APIMQTTCassandraServerName string  `json:"apiMqttCassandraServerName"`
	APIMQTTPort                int     `json:"apiMqttPort"`
	MessageServiceType         *string `json:"messageServiceType"`
	TelegramAPIToken           string  `json:"telegramApiToken"`
	TelegramChatID             string  `json:"telegramChatId"`
	PushoverAPIToken           string  `json:"pushoverApiToken"`
	PushoverAppName            string  `json:"pushoverAppName"`
	RobotPositionMode          string  `json:"robotPositionMode"`
	Longtitude                 Float   `json:"longtitude"`
	Latitude                   Float   `json:"latitude"`
	TransitSpeedSetPoint       Float   `json:"transitSpeedSetPoint"`
	MowSpeedSetPoint           Float   `json:"mowSpeedSetPoint"`
	FixTimeout                 int     `json:"fixTimeout"`
	MinVoltage                 Float   `json:"minVoltage"`
	MaxVoltage                 Float   `json:"maxVoltage"`
	ChargeCurrentThd           Float   `json:"chargeCurrentThd"`
	DataMaxAge                 int     `json:"dataMaxAge"`
	OfflineTimeout             int     `json:"offlineTimeout"`
}

// dataMaxAgeDays is reported for legacy's data retention; the statistics
// keep their samples a year.
const dataMaxAgeDays = 365

// legacyKind is the connection type as the app knows it. The app has no
// simulator: it is shown as HTTP and only changed by choosing another type.
func legacyKind(kind string) string {
	switch kind {
	case settings.LinkMQTT:
		return "MQTT"
	case settings.LinkUART:
		return "UART"
	default:
		return "HTTP"
	}
}

func hostPort(rawURL string, defaultPort int) (string, int) {
	u, err := url.Parse(rawURL)
	if err != nil || u.Host == "" {
		return rawURL, defaultPort
	}
	port := defaultPort
	if p, err := strconv.Atoi(u.Port()); err == nil {
		port = p
	}
	return u.Hostname(), port
}

func (a *API) settingsJSON() SettingsJSON {
	s := a.settings.Get()
	c, r, b := s.Connection, s.Rover, s.Battery
	httpHost, _ := hostPort(c.HTTPURL, 80)
	mqttHost, mqttPort := hostPort(c.MQTTBroker, 1883)
	apiHost, apiPort := hostPort(s.API.Broker, 1883)
	var apiType *string
	if s.API.Enabled {
		t := "MQTT"
		apiType = &t
	}
	mode := "relative"
	if r.AbsolutePosition {
		mode = "absolute"
	}
	var service *string
	if n := s.Notify.Service; n != settings.NotifyOff {
		service = &n
	}
	return SettingsJSON{
		MessageServiceType: service, TelegramChatID: s.Notify.TelegramChatID, PushoverAppName: s.Notify.PushoverUser,
		RobotConnectionType: legacyKind(c.Kind),
		HTTPRobotIPAdress:   httpHost,
		MQTTClientID:        c.MQTTClientID, MQTTUser: c.MQTTUser, MQTTServer: mqttHost, MQTTPort: mqttPort,
		MQTTMowerNameWithPrefix: c.MQTTMower,
		UARTPort:                c.UARTPort, UARTBaudrate: c.UARTBaud,
		APIType:         apiType,
		APIMQTTClientID: s.API.ClientID, APIMQTTUser: s.API.User, APIMQTTServer: apiHost, APIMQTTPort: apiPort,
		APIMQTTCassandraServerName: s.API.ServerName,
		RobotPositionMode:          mode, Longtitude: Float(r.Lon), Latitude: Float(r.Lat),
		TransitSpeedSetPoint: Float(r.GotoSpeedMps), MowSpeedSetPoint: Float(r.MowSpeedMps), FixTimeout: r.FixTimeoutSec,
		MinVoltage: Float(b.EmptyV), MaxVoltage: Float(b.FullV), ChargeCurrentThd: Float(b.ChargingBelowA),
		DataMaxAge: dataMaxAgeDays, OfflineTimeout: b.OfflineAfterSec,
	}
}

// settingsCommand answers "update" and stores setComm, setRover and
// setApp; each changed key is taken, the others stay.
func (a *API) settingsCommand(c command) ([]Message, error) {
	answer := func() []Message { return []Message{{"settings", mustJSON(a.settingsJSON())}} }
	if c.Command == "update" {
		return answer(), nil
	}
	var v map[string]json.RawMessage
	if err := json.Unmarshal(c.Value, &v); err != nil {
		return nil, fmt.Errorf("%w: settings %s wants an object: %w", ErrInvalid, c.Command, err)
	}
	s := a.settings.Get()
	var err error
	switch c.Command {
	case "setComm":
		err = setComm(&s, v)
	case "setRover":
		err = setRover(&s, v)
	case "setApp":
		err = setApp(&s, v)
	default:
		return nil, fmt.Errorf("%w: settings command %q", ErrUnknown, c.Command)
	}
	if err != nil {
		return nil, err
	}
	if err := a.settings.Set(s); err != nil {
		return nil, err
	}
	return answer(), nil
}

// fields reads the values of known keys; a key with another type is an error.
type fields map[string]json.RawMessage

func (f fields) str(key string, dst *string) error {
	raw, ok := f[key]
	if !ok || string(raw) == "null" {
		return nil
	}
	if err := json.Unmarshal(raw, dst); err != nil {
		return fmt.Errorf("%w: %s: %w", ErrInvalid, key, err)
	}
	return nil
}

// secret keeps the stored value when the app sends an empty one.
func (f fields) secret(key string, dst *string) error {
	var v string
	if err := f.str(key, &v); err != nil {
		return err
	}
	if v != "" {
		*dst = v
	}
	return nil
}

func (f fields) num(key string, dst *float64) error {
	raw, ok := f[key]
	if !ok || string(raw) == "null" {
		return nil
	}
	// The app sends numbers, sometimes as text.
	var s string
	if json.Unmarshal(raw, &s) == nil {
		v, err := strconv.ParseFloat(strings.TrimSpace(s), 64)
		if err != nil {
			return fmt.Errorf("%w: %s: %q is not a number", ErrInvalid, key, s)
		}
		*dst = v
		return nil
	}
	if err := json.Unmarshal(raw, dst); err != nil {
		return fmt.Errorf("%w: %s: %w", ErrInvalid, key, err)
	}
	return nil
}

func (f fields) integer(key string, dst *int) error {
	v := float64(*dst)
	if err := f.num(key, &v); err != nil {
		return err
	}
	*dst = int(v)
	return nil
}

func setComm(s *settings.Settings, raw map[string]json.RawMessage) error {
	f := fields(raw)
	c := &s.Connection
	var kind string
	if err := f.str("robotConnectionType", &kind); err != nil {
		return err
	}
	if kind != "" && !strings.EqualFold(kind, legacyKind(c.Kind)) {
		switch strings.ToUpper(kind) {
		case "HTTP":
			c.Kind = settings.LinkHTTP
		case "MQTT":
			c.Kind = settings.LinkMQTT
		case "UART":
			c.Kind = settings.LinkUART
		default:
			return fmt.Errorf("%w: robotConnectionType %q", ErrInvalid, kind)
		}
	}
	httpHost, _ := hostPort(c.HTTPURL, 80)
	mqttHost, mqttPort := hostPort(c.MQTTBroker, 1883)
	apiHost, apiPort := hostPort(s.API.Broker, 1883)
	var httpPass string
	errs := []error{
		f.str("httpRobotIpAdress", &httpHost), f.secret("httpRobotPassword", &httpPass),
		f.str("mqttClientId", &c.MQTTClientID), f.str("mqttUser", &c.MQTTUser), f.secret("mqttPassword", &c.MQTTPassword),
		f.str("mqttServer", &mqttHost), f.integer("mqttPort", &mqttPort), f.str("mqttMowerNameWithPrefix", &c.MQTTMower),
		f.str("uartPort", &c.UARTPort), f.integer("uartBaudrate", &c.UARTBaud),
		f.str("apiMqttClientId", &s.API.ClientID), f.str("apiMqttUser", &s.API.User), f.secret("apiMqttPassword", &s.API.Password),
		f.str("apiMqttServer", &apiHost), f.integer("apiMqttPort", &apiPort),
		f.str("apiMqttCassandraServerName", &s.API.ServerName),
		f.secret("telegramApiToken", &s.Notify.TelegramToken), f.str("telegramChatId", &s.Notify.TelegramChatID),
		f.secret("pushoverApiToken", &s.Notify.PushoverToken), f.str("pushoverAppName", &s.Notify.PushoverUser),
	}
	for _, err := range errs {
		if err != nil {
			return err
		}
	}
	if httpPass != "" {
		p, err := strconv.Atoi(httpPass)
		if err != nil {
			return fmt.Errorf("%w: httpRobotPassword must be a number", ErrInvalid)
		}
		c.HTTPPassword = p
	}
	if _, ok := raw["messageServiceType"]; ok {
		var t string
		_ = f.str("messageServiceType", &t)
		switch strings.ToLower(t) {
		case "telegram":
			s.Notify.Service = settings.NotifyTelegram
		case "pushover":
			s.Notify.Service = settings.NotifyPushover
		default:
			s.Notify.Service = settings.NotifyOff
		}
	}
	if _, ok := raw["apiType"]; ok {
		var t string
		_ = f.str("apiType", &t)
		s.API.Enabled = strings.EqualFold(t, "MQTT")
	}
	if httpHost != "" {
		c.HTTPURL = withScheme("http", httpHost, 0)
	}
	if mqttHost != "" {
		c.MQTTBroker = withScheme("tcp", mqttHost, mqttPort)
	}
	if apiHost != "" {
		s.API.Broker = withScheme("tcp", apiHost, apiPort)
	}
	return nil
}

// withScheme makes a URL of a legacy host ("192.168.1.5" or
// "http://192.168.1.5") and port (0 = none).
func withScheme(scheme, host string, port int) string {
	if strings.Contains(host, "://") {
		return host
	}
	if port > 0 {
		host = net.JoinHostPort(host, strconv.Itoa(port))
	}
	return scheme + "://" + host
}

func setRover(s *settings.Settings, raw map[string]json.RawMessage) error {
	f := fields(raw)
	var mode string
	if err := f.str("robotPositionMode", &mode); err != nil {
		return err
	}
	switch mode {
	case "absolute":
		s.Rover.AbsolutePosition = true
	case "relative":
		s.Rover.AbsolutePosition = false
	}
	if err := f.num("longtitude", &s.Rover.Lon); err != nil {
		return err
	}
	return f.num("latitude", &s.Rover.Lat)
}

func setApp(s *settings.Settings, raw map[string]json.RawMessage) error {
	f := fields(raw)
	for _, err := range []error{
		f.num("minVoltage", &s.Battery.EmptyV), f.num("maxVoltage", &s.Battery.FullV),
		f.num("chargeCurrentThd", &s.Battery.ChargingBelowA), f.integer("offlineTimeout", &s.Battery.OfflineAfterSec),
	} {
		if err != nil {
			return err
		}
	}
	return nil // dataMaxAge: the statistics keep a year
}
