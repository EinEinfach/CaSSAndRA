package mqttapi_test

import (
	"context"
	"errors"
	"slices"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/mqttapi"
	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

func setSettings(t *testing.T, f *fixture, change func(s *settings.Settings)) {
	t.Helper()
	s := f.settings.Get()
	change(&s)
	if err := f.settings.Set(s); err != nil {
		t.Fatal(err)
	}
}

func TestSettingsUpdateNeverSendsPasswords(t *testing.T) {
	f := newFixture(t)
	setSettings(t, f, func(s *settings.Settings) {
		s.Connection = settings.Connection{
			Kind: settings.LinkMQTT, HTTPURL: "http://192.168.1.50", HTTPPassword: 123456,
			MQTTBroker: "tcp://192.168.1.10:1884", MQTTMower: "Ardumower", MQTTClientID: "cas", MQTTUser: "me", MQTTPassword: "secret",
			UARTPort: "/dev/ttyACM0", UARTBaud: 115200,
		}
		s.API = settings.API{Enabled: true, Broker: "tcp://broker.local:1883", ServerName: "Garden", ClientID: "api", User: "u", Password: "apisecret"}
		s.Rover.AbsolutePosition, s.Rover.Lon, s.Rover.Lat = true, 13.4, 52.5
	})
	got := payloads(handle(t, f.api, `{"settings": {"command": "update", "value": []}}`), "settings")
	want := `{"robotConnectionType":"MQTT","httpRobotIpAdress":"192.168.1.50","httpRobotPassword":"",` +
		`"mqttClientId":"cas","mqttUser":"me","mqttPassword":"","mqttServer":"192.168.1.10","mqttPort":1884,` +
		`"mqttMowerNameWithPrefix":"Ardumower","uartPort":"/dev/ttyACM0","uartBaudrate":115200,"apiType":"MQTT",` +
		`"apiMqttClientId":"api","apiMqttUser":"u","apiMqttPassword":"","apiMqttServer":"broker.local",` +
		`"apiMqttCassandraServerName":"Garden","apiMqttPort":1883,"messageServiceType":null,"telegramApiToken":"",` +
		`"telegramChatId":"","pushoverApiToken":"","pushoverAppName":"","robotPositionMode":"absolute",` +
		`"longtitude":13.4,"latitude":52.5,"transitSpeedSetPoint":0.3,"mowSpeedSetPoint":0.25,"fixTimeout":60,` +
		`"minVoltage":22.0,"maxVoltage":28.0,"chargeCurrentThd":-0.03,"dataMaxAge":365,"offlineTimeout":60}`
	if len(got) != 1 || got[0] != want {
		t.Errorf("settings\n got %v\nwant %s", got, want)
	}
	for _, secret := range []string{"secret", "123456", "apisecret"} {
		if strings.Contains(got[0], secret) {
			t.Errorf("settings contain %q", secret)
		}
	}
}

func TestSetComm(t *testing.T) {
	f := newFixture(t) // the simulator
	// The app shows the simulator as HTTP; saving that unchanged keeps it.
	handle(t, f.api, `{"settings": {"command": "setComm", "value": {"robotConnectionType": "HTTP",
		"httpRobotIpAdress": "192.168.1.60", "httpRobotPassword": "", "apiType": "MQTT", "apiMqttServer": "10.0.0.2",
		"apiMqttPort": 1885, "apiMqttCassandraServerName": "Garden", "apiMqttPassword": "new"}}}`)
	s := f.settings.Get()
	if s.Connection.Kind != settings.LinkSim || s.Connection.HTTPURL != "http://192.168.1.60" ||
		!s.API.Enabled || s.API.Broker != "tcp://10.0.0.2:1885" || s.API.ServerName != "Garden" || s.API.Password != "new" {
		t.Errorf("after setComm: %+v %+v", s.Connection, s.API)
	}
	// Choosing another type switches; an empty password keeps the old one.
	handle(t, f.api, `{"settings": {"command": "setComm", "value": {"robotConnectionType": "MQTT",
		"mqttServer": "192.168.1.10", "mqttPort": "1883", "mqttMowerNameWithPrefix": "Alfred", "mqttClientId": "c",
		"apiMqttPassword": "", "apiType": null}}}`)
	s = f.settings.Get()
	if s.Connection.Kind != settings.LinkMQTT || s.Connection.MQTTBroker != "tcp://192.168.1.10:1883" ||
		s.Connection.MQTTMower != "Alfred" || s.API.Password != "new" || s.API.Enabled {
		t.Errorf("after the second setComm: %+v %+v", s.Connection, s.API)
	}
}

func TestSetRoverAndApp(t *testing.T) {
	f := newFixture(t)
	handle(t, f.api, `{"settings": {"command": "setRover", "value": {"robotPositionMode": "absolute", "longtitude": 13.5, "latitude": "52.4"}}}`)
	handle(t, f.api, `{"settings": {"command": "setApp", "value": {"minVoltage": 21.5, "maxVoltage": 29, "chargeCurrentThd": -0.05, "dataMaxAge": 10, "offlineTimeout": 120}}}`)
	s := f.settings.Get()
	if !s.Rover.AbsolutePosition || s.Rover.Lon != 13.5 || s.Rover.Lat != 52.4 ||
		s.Battery.EmptyV != 21.5 || s.Battery.FullV != 29 || s.Battery.ChargingBelowA != -0.05 || s.Battery.OfflineAfterSec != 120 {
		t.Errorf("settings = %+v %+v", s.Rover, s.Battery)
	}
}

func TestInvalidSettingsAreNotStored(t *testing.T) {
	for _, cmd := range []string{
		`{"settings": {"command": "setApp", "value": {"minVoltage": 30, "maxVoltage": 20}}}`,
		`{"settings": {"command": "setRover", "value": {"latitude": "north"}}}`,
		`{"settings": {"command": "setComm", "value": {"robotConnectionType": "CARRIER_PIGEON"}}}`,
		`{"settings": {"command": "setComm", "value": {"httpRobotPassword": "abc"}}}`,
		`{"settings": {"command": "setApp", "value": []}}`,
	} {
		f := newFixture(t)
		before := f.settings.Get()
		if _, err := f.api.Handle(context.Background(), []byte(cmd)); err == nil {
			t.Errorf("%s: no error", cmd)
		}
		if f.settings.Get() != before {
			t.Errorf("%s: stored", cmd)
		}
	}
}

func TestServerTopicAndCommands(t *testing.T) {
	f := newFixture(t)
	load, temp, mem := 12.345, 48.3, 25.0
	f.system.info.CPULoadPercent, f.system.info.CPUTempC, f.system.info.MemUsedPercent = &load, &temp, &mem
	if got := string(topic(t, f.api.State(), "server")); got != `{"software":"CaSSAndRA","version":"test","cpuLoad":12.35,"cpuTemp":48.3,"memUsage":25.0,"hddUsage":null}` {
		t.Errorf("server = %s", got)
	}
	handle(t, f.api, `{"server": {"command": "restart", "value": []}}`)
	handle(t, f.api, `{"server": {"command": "sendMessage", "value": ["hi"]}}`)
	handle(t, f.api, `{"server": {"command": "shutdown", "value": []}}`)
	if f.restarts != 1 || !slices.Equal(f.powerOff, []string{"power off"}) || len(f.robot.recorded()) != 0 {
		t.Errorf("restarts %d, power off %v, robot %v", f.restarts, f.powerOff, f.robot.recorded())
	}
	// With the robot on the serial port, the robot goes first.
	setSettings(t, f, func(s *settings.Settings) { s.Connection.Kind = settings.LinkUART })
	handle(t, f.api, `{"server": {"command": "shutdown", "value": []}}`)
	if !slices.Equal(f.robot.recorded(), []string{"shutdown"}) || len(f.powerOff) != 2 {
		t.Errorf("robot %v, power off %v", f.robot.recorded(), f.powerOff)
	}
}

func TestServerCommandsNeedTheirFunctions(t *testing.T) {
	r := &fakeRobot{snap: mowing()}
	api := mqttapi.New(deps(t, r), mqttapi.Config{})
	for _, cmd := range []string{"restart", "shutdown"} {
		if _, err := api.Handle(context.Background(), []byte(`{"server": {"command": "`+cmd+`", "value": []}}`)); !errors.Is(err, mqttapi.ErrUnknown) {
			t.Errorf("%s without function: %v", cmd, err)
		}
	}
}
