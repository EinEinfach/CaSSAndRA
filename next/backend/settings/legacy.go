package settings

import (
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/EinEinfach/CaSSAndRA/next/backend/jsonfile"
)

// ImportLegacy reads the settings of legacy CaSSAndRA from userDir (the
// "user" folder of its data directory, e.g. ~/.cassandra/user). Sections
// without a file keep their defaults. A section with invalid values also
// keeps its defaults and is reported in warnings. found is false if none of
// the legacy files exists.
func ImportLegacy(userDir string) (s Settings, found bool, warnings []string, err error) {
	s = Default()
	sections := []struct {
		file  string
		apply func(raw map[string]json.RawMessage, s *Settings) error
	}{
		{"commcfg.json", applyComm},
		{"rovercfg.json", applyRover},
		{"appcfg.json", applyApp},
		{"pathplannercfg.json", applyPlanner},
	}
	for _, sec := range sections {
		var raw map[string]json.RawMessage
		err := jsonfile.Read(filepath.Join(userDir, sec.file), &raw)
		if errors.Is(err, os.ErrNotExist) {
			continue
		}
		found = true
		if err != nil {
			warnings = append(warnings, fmt.Sprintf("%s: %v", sec.file, err))
			continue
		}
		next := s
		if err := sec.apply(raw, &next); err != nil {
			warnings = append(warnings, fmt.Sprintf("%s: %v", sec.file, err))
			continue
		}
		if err := next.Validate(); err != nil {
			warnings = append(warnings, fmt.Sprintf("%s: kept defaults: %v", sec.file, err))
			continue
		}
		s = next
	}
	return s, found, warnings, nil
}

// legacyList reads the legacy format [{"KEY": value}, {"KEY2": value2}].
func legacyList(raw json.RawMessage) (map[string]json.RawMessage, error) {
	var list []map[string]json.RawMessage
	if err := json.Unmarshal(raw, &list); err != nil {
		return nil, err
	}
	out := map[string]json.RawMessage{}
	for _, item := range list {
		for k, v := range item {
			out[k] = v
		}
	}
	return out, nil
}

// decoder collects the first error, so the apply functions stay linear.
type decoder struct {
	raw map[string]json.RawMessage
	err error
}

// get decodes key into v if present and not null.
func (d *decoder) get(key string, v any) {
	r, ok := d.raw[key]
	if !ok || d.err != nil || string(r) == "null" {
		return
	}
	if err := json.Unmarshal(r, v); err != nil {
		d.err = fmt.Errorf("%s: %w", key, err)
	}
}

// str decodes a string, accepting numbers too (legacy stored some as either).
func (d *decoder) str(key string) string {
	var v any
	d.get(key, &v)
	switch x := v.(type) {
	case string:
		return x
	case float64:
		return strconv.FormatFloat(x, 'f', -1, 64)
	}
	return ""
}

func (d *decoder) list(key string) *decoder {
	sub := &decoder{err: d.err}
	if r, ok := d.raw[key]; ok && d.err == nil && string(r) != "null" {
		sub.raw, sub.err = legacyList(r)
		if sub.err != nil {
			sub.err = fmt.Errorf("%s: %w", key, sub.err)
		}
	}
	return sub
}

func brokerURL(server, port string) string {
	if server == "" {
		return ""
	}
	if port == "" {
		port = "1883"
	}
	return "tcp://" + net.JoinHostPort(server, port)
}

func applyComm(raw map[string]json.RawMessage, s *Settings) error {
	d := &decoder{raw: raw}
	c := &s.Connection
	switch use := strings.ToUpper(d.str("USE")); use {
	case "HTTP":
		c.Kind = LinkHTTP
	case "MQTT":
		c.Kind = LinkMQTT
	case "UART":
		c.Kind = LinkUART
	case "":
	default:
		return fmt.Errorf("USE: unknown connection %q", use)
	}

	httpCfg := d.list("HTTP")
	c.HTTPURL = httpCfg.str("IP")
	if c.HTTPURL != "" && !strings.Contains(c.HTTPURL, "://") {
		c.HTTPURL = "http://" + c.HTTPURL
	}
	if pw := httpCfg.str("PASSWORD"); pw != "" {
		n, err := strconv.Atoi(pw)
		if err != nil {
			return fmt.Errorf("HTTP password %q is not a number", pw)
		}
		c.HTTPPassword = n
	}

	uart := d.list("UART")
	if port := uart.str("SERPORT"); port != "" {
		c.UARTPort = port
	}
	uart.get("BAUDRATE", &c.UARTBaud)

	mqtt := d.list("MQTT")
	if id := mqtt.str("CLIENT_ID"); id != "" {
		c.MQTTClientID = id
	}
	c.MQTTUser = mqtt.str("USERNAME")
	c.MQTTPassword = mqtt.str("PASSWORD")
	c.MQTTBroker = brokerURL(mqtt.str("MQTT_SERVER"), mqtt.str("PORT"))
	if name := mqtt.str("MOWER_NAME"); name != "" {
		c.MQTTMower = name
	}

	a := &s.API
	a.Enabled = strings.EqualFold(d.str("API"), "MQTT")
	api := d.list("MQTT_API")
	if id := api.str("CLIENT_ID"); id != "" {
		a.ClientID = id
	}
	a.User = api.str("USERNAME")
	a.Password = api.str("PASSWORD")
	a.Broker = brokerURL(api.str("MQTT_SERVER"), api.str("PORT"))
	if name := api.str("API_SERVER_NAME"); name != "" {
		a.ServerName = name
	}
	for _, sub := range []*decoder{d, httpCfg, uart, mqtt, api} {
		if sub.err != nil {
			return sub.err
		}
	}
	return nil
}

func applyRover(raw map[string]json.RawMessage, s *Settings) error {
	d := &decoder{raw: raw}
	r := &s.Rover
	d.get("mowspeed_setpoint", &r.MowSpeedMps)
	d.get("gotospeed_setpoint", &r.GotoSpeedMps)
	d.get("fix_timeout", &r.FixTimeoutSec)
	d.get("finish_and_restart", &r.FinishAndRestart)
	r.AbsolutePosition = d.str("positionmode") == "absolute"
	d.get("lon", &r.Lon)
	d.get("lat", &r.Lat)
	return d.err
}

func applyApp(raw map[string]json.RawMessage, s *Settings) error {
	d := &decoder{raw: raw}
	b := &s.Battery
	d.get("time_to_offline", &b.OfflineAfterSec)
	d.get("current_thd_charge", &b.ChargingBelowA)
	var soc []struct {
		V   float64 `json:"V"`
		SoC float64 `json:"SoC"`
	}
	d.get("voltage_to_soc", &soc)
	for _, p := range soc {
		switch p.SoC {
		case 0:
			b.EmptyV = p.V
		case 100:
			b.FullV = p.V
		}
	}
	return d.err
}

func applyPlanner(raw map[string]json.RawMessage, s *Settings) error {
	d := &decoder{raw: raw}
	p := &s.Planner
	d.get("pattern", &p.Pattern)
	d.get("width", &p.WidthM)
	d.get("angle", &p.AngleDeg)
	d.get("distancetoborder", &p.DistanceToBorder)
	d.get("mowarea", &p.MowArea)
	d.get("mowborder", &p.BorderLaps)
	d.get("mowexclusion", &p.MowExclusions)
	d.get("mowborderccw", &p.BorderCCW)
	return d.err
}
