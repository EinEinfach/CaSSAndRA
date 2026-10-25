package settings_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

// testdata/legacy holds files in the format of legacy CaSSAndRA 0.302
// (CaSSAndRA/src/data/user/*.json and backend/data/cfgdata.py).
func TestImportLegacy(t *testing.T) {
	got, found, warnings, err := settings.ImportLegacy("testdata/legacy/user")
	if err != nil || !found || len(warnings) > 0 {
		t.Fatalf("found = %v, warnings = %v, err = %v", found, warnings, err)
	}
	want := settings.Settings{
		Connection: settings.Connection{
			Kind: settings.LinkHTTP, HTTPURL: "http://192.168.2.26", HTTPPassword: 123456,
			UARTPort: "/dev/ttyUSB0", UARTBaud: 19200,
			MQTTBroker: "tcp://192.168.2.21:1884", MQTTMower: "Robo", MQTTClientID: "Robo_MQTT",
			MQTTUser: "bridge", MQTTPassword: "bridgepw",
		},
		Rover: settings.Rover{
			MowSpeedMps: 0.4, GotoSpeedMps: 0.5, FixTimeoutSec: 90, FinishAndRestart: true,
			AbsolutePosition: true, Lon: 13.4, Lat: 52.5,
		},
		Battery: settings.Battery{EmptyV: 20.4, FullV: 28, ChargingBelowA: -0.05, OfflineAfterSec: 30},
		Planner: settings.Planner{
			Pattern: settings.PatternSquares, WidthM: 0.16, AngleDeg: 15, DistanceToBorder: 2,
			MowArea: false, BorderLaps: 3, MowExclusions: false, BorderCCW: true,
		},
		API: settings.API{
			Enabled: true, Broker: "tcp://192.168.2.30:1883", ServerName: "Garden",
			ClientID: "DevServer", User: "api", Password: "apipw",
		},
		Broker:     settings.Default().Broker, // legacy had none
		Appearance: settings.Appearance{RobotPicture: "alfred", RobotSizeCm: 130},
	}
	if got != want {
		t.Errorf("got  %+v\nwant %+v", got, want)
	}
}

func TestImportLegacyMissingFilesKeepDefaults(t *testing.T) {
	got, found, warnings, err := settings.ImportLegacy("testdata/legacy_partial/user")
	if err != nil || !found || len(warnings) > 0 {
		t.Fatalf("found = %v, warnings = %v, err = %v", found, warnings, err)
	}
	want := settings.Default()
	want.Rover.MowSpeedMps = 0.35
	if got != want {
		t.Errorf("got  %+v\nwant %+v", got, want)
	}
}

func TestImportLegacyNothingThere(t *testing.T) {
	got, found, warnings, err := settings.ImportLegacy(t.TempDir())
	if err != nil || found || len(warnings) > 0 || got != settings.Default() {
		t.Errorf("found = %v, warnings = %v, err = %v, settings changed = %v", found, warnings, err, got != settings.Default())
	}
}

func TestImportLegacyBadSectionsKeepDefaults(t *testing.T) {
	got, found, warnings, err := settings.ImportLegacy("testdata/legacy_invalid/user")
	if err != nil || !found {
		t.Fatalf("found = %v, err = %v", found, err)
	}
	if got != settings.Default() {
		t.Errorf("got %+v, want defaults for every broken section", got)
	}
	for _, file := range []string{"commcfg.json", "rovercfg.json", "appcfg.json", "pathplannercfg.json"} {
		if !containsPrefix(warnings, file) {
			t.Errorf("no warning for %s in %q", file, warnings)
		}
	}
}

func containsPrefix(list []string, prefix string) bool {
	for _, s := range list {
		if strings.HasPrefix(s, prefix) {
			return true
		}
	}
	return false
}

func TestImportLegacyCommVariants(t *testing.T) {
	tests := []struct {
		name, comm string
		check      func(s settings.Settings) bool
		warn       bool
	}{
		{"ip without scheme", `{"USE": "HTTP", "HTTP": [{"IP": "10.0.0.5"}, {"PASSWORD": 42}]}`,
			func(s settings.Settings) bool {
				return s.Connection.HTTPURL == "http://10.0.0.5" && s.Connection.HTTPPassword == 42
			}, false},
		{"mqtt without port", `{"USE": "mqtt", "MQTT": [{"MQTT_SERVER": "broker"}, {"MOWER_NAME": "M"}]}`,
			func(s settings.Settings) bool {
				return s.Connection.Kind == settings.LinkMQTT && s.Connection.MQTTBroker == "tcp://broker:1883"
			}, false},
		{"uart", `{"USE": "UART", "UART": [{"SERPORT": "/dev/ttyS0"}, {"BAUDRATE": 9600}]}`,
			func(s settings.Settings) bool {
				return s.Connection.Kind == settings.LinkUART && s.Connection.UARTBaud == 9600
			}, false},
		{"unknown connection", `{"USE": "BLUETOOTH"}`, nil, true},
		{"password not a number", `{"USE": "HTTP", "HTTP": [{"IP": "h"}, {"PASSWORD": "abc"}]}`, nil, true},
		{"list is not a list", `{"HTTP": {"IP": "h"}}`, nil, true},
		{"value of wrong type", `{"UART": [{"BAUDRATE": "fast"}]}`, nil, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dir := t.TempDir()
			if err := os.WriteFile(filepath.Join(dir, "commcfg.json"), []byte(tt.comm), 0o600); err != nil {
				t.Fatal(err)
			}
			got, _, warnings, err := settings.ImportLegacy(dir)
			if err != nil {
				t.Fatal(err)
			}
			if tt.warn {
				if len(warnings) != 1 || got.Connection != settings.Default().Connection {
					t.Errorf("warnings = %q, connection = %+v, want a warning and defaults", warnings, got.Connection)
				}
				return
			}
			if len(warnings) > 0 || !tt.check(got) {
				t.Errorf("warnings = %q, connection = %+v", warnings, got.Connection)
			}
		})
	}
}
