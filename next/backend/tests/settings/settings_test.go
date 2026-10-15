package settings_test

import (
	"errors"
	"math"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

func TestDefaultIsValid(t *testing.T) {
	d := settings.Default()
	if err := d.Validate(); err != nil {
		t.Fatal(err)
	}
	if d.Connection.Kind != settings.LinkSim {
		t.Errorf("default connection = %q, want the simulator", d.Connection.Kind)
	}
}

func TestValidate(t *testing.T) {
	tests := []struct {
		name   string
		change func(s *settings.Settings)
		want   string // part of the error, "" = valid
	}{
		{"http", func(s *settings.Settings) {
			s.Connection.Kind, s.Connection.HTTPURL = settings.LinkHTTP, "http://192.168.1.50"
		}, ""},
		{"http without url", func(s *settings.Settings) { s.Connection.Kind = settings.LinkHTTP }, "connection.httpUrl"},
		{"http with ip only", func(s *settings.Settings) {
			s.Connection.Kind, s.Connection.HTTPURL = settings.LinkHTTP, "192.168.1.50"
		}, "connection.httpUrl"},
		{"negative http password", func(s *settings.Settings) { s.Connection.HTTPPassword = -1 }, "httpPassword"},
		{"uart", func(s *settings.Settings) { s.Connection.Kind = settings.LinkUART }, ""},
		{"uart without port", func(s *settings.Settings) {
			s.Connection.Kind, s.Connection.UARTPort = settings.LinkUART, ""
		}, "connection.uartPort"},
		{"uart without baud", func(s *settings.Settings) {
			s.Connection.Kind, s.Connection.UARTBaud = settings.LinkUART, 0
		}, "connection.uartBaud"},
		{"mqtt", func(s *settings.Settings) {
			s.Connection.Kind, s.Connection.MQTTBroker = settings.LinkMQTT, "tcp://10.0.0.1:1883"
		}, ""},
		{"mqtt without broker", func(s *settings.Settings) { s.Connection.Kind = settings.LinkMQTT }, "connection.mqttBroker"},
		{"mqtt without mower", func(s *settings.Settings) {
			s.Connection.Kind, s.Connection.MQTTBroker, s.Connection.MQTTMower = settings.LinkMQTT, "tcp://h:1", " "
		}, "connection.mqttMower"},
		{"mqtt without client id", func(s *settings.Settings) {
			s.Connection.Kind, s.Connection.MQTTBroker, s.Connection.MQTTClientID = settings.LinkMQTT, "tcp://h:1", ""
		}, "connection.mqttClientId"},
		{"unknown connection", func(s *settings.Settings) { s.Connection.Kind = "wifi" }, "connection.kind"},
		{"mow speed too fast", func(s *settings.Settings) { s.Rover.MowSpeedMps = 1.5 }, "rover.mowSpeedMps"},
		{"goto speed NaN", func(s *settings.Settings) { s.Rover.GotoSpeedMps = math.NaN() }, "rover.gotoSpeedMps"},
		{"negative fix timeout", func(s *settings.Settings) { s.Rover.FixTimeoutSec = -1 }, "rover.fixTimeoutSec"},
		{"lon", func(s *settings.Settings) { s.Rover.Lon = 181 }, "rover.lon"},
		{"lat", func(s *settings.Settings) { s.Rover.Lat = -91 }, "rover.lat"},
		{"battery empty above full", func(s *settings.Settings) { s.Battery.EmptyV = 29 }, "battery.emptyV"},
		{"positive charging current", func(s *settings.Settings) { s.Battery.ChargingBelowA = 0.1 }, "battery.chargingBelowA"},
		{"offline too fast", func(s *settings.Settings) { s.Battery.OfflineAfterSec = 1 }, "battery.offlineAfterSec"},
		{"pattern", func(s *settings.Settings) { s.Planner.Pattern = "spiral" }, "planner.pattern"},
		{"width", func(s *settings.Settings) { s.Planner.WidthM = 0 }, "planner.widthM"},
		{"angle", func(s *settings.Settings) { s.Planner.AngleDeg = 400 }, "planner.angleDeg"},
		{"distance to border", func(s *settings.Settings) { s.Planner.DistanceToBorder = -1 }, "planner.distanceToBorder"},
		{"border laps", func(s *settings.Settings) { s.Planner.BorderLaps = 11 }, "planner.borderLaps"},
		{"api disabled needs nothing", func(s *settings.Settings) { s.API = settings.API{} }, ""},
		{"api", func(s *settings.Settings) { s.API.Enabled, s.API.Broker = true, "tcp://10.0.0.1:1883" }, ""},
		{"api without broker", func(s *settings.Settings) { s.API.Enabled = true }, "api.broker"},
		{"api without name", func(s *settings.Settings) {
			s.API.Enabled, s.API.Broker, s.API.ServerName = true, "tcp://h:1", ""
		}, "api.serverName"},
		{"api without client id", func(s *settings.Settings) {
			s.API.Enabled, s.API.Broker, s.API.ClientID = true, "tcp://h:1", ""
		}, "api.clientId"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := settings.Default()
			tt.change(&s)
			err := s.Validate()
			if tt.want == "" {
				if err != nil {
					t.Errorf("unexpected error: %v", err)
				}
				return
			}
			if !errors.Is(err, settings.ErrInvalid) || !strings.Contains(err.Error(), tt.want) {
				t.Errorf("err = %v, want ErrInvalid mentioning %q", err, tt.want)
			}
		})
	}
}

func TestValidateReportsAllProblems(t *testing.T) {
	s := settings.Default()
	s.Rover.MowSpeedMps, s.Planner.WidthM = 0, 0
	err := s.Validate()
	if err == nil || !strings.Contains(err.Error(), "rover.mowSpeedMps") || !strings.Contains(err.Error(), "planner.widthM") {
		t.Errorf("err = %v, want both problems", err)
	}
}
