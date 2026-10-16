// Package settings holds the user settings (connection, rover, battery,
// planner), stores them as JSON and imports them from legacy CaSSAndRA.
package settings

import (
	"errors"
	"fmt"
	"math"
	"net/url"
	"slices"
	"strings"
)

// Connection kinds.
const (
	LinkSim  = "sim"
	LinkHTTP = "http"
	LinkUART = "uart"
	LinkMQTT = "mqtt"
)

// Mow patterns of the planner.
const (
	PatternLines   = "lines"
	PatternSquares = "squares"
	PatternRings   = "rings"
)

// Robot pictures on the map (web/static/rovers/<name>.png, from legacy CaSSAndRA).
var RobotPictures = []string{"default", "ardumower", "alfred", "landrumower"}

// Settings are all user settings. The zero value is invalid; start from Default.
type Settings struct {
	Connection Connection `json:"connection"`
	Rover      Rover      `json:"rover"`
	Battery    Battery    `json:"battery"`
	Planner    Planner    `json:"planner"`
	API        API        `json:"api"`
	Appearance Appearance `json:"appearance"`
}

// Connection selects how CaSSAndRA talks to the robot.
type Connection struct {
	Kind string `json:"kind"` // LinkSim, LinkHTTP, LinkUART or LinkMQTT
	// HTTP: robot URL and the password from the firmware's config.h (0 = none).
	HTTPURL      string `json:"httpUrl"`
	HTTPPassword int    `json:"httpPassword"`
	UARTPort     string `json:"uartPort"`
	UARTBaud     int    `json:"uartBaud"`
	// MQTT: broker URL (tcp://host:1883) and the topic prefix of the robot's bridge.
	MQTTBroker   string `json:"mqttBroker"`
	MQTTMower    string `json:"mqttMower"`
	MQTTClientID string `json:"mqttClientId"`
	MQTTUser     string `json:"mqttUser"`
	MQTTPassword string `json:"mqttPassword"`
}

// Rover holds the driving parameters sent with mow and goto commands.
type Rover struct {
	MowSpeedMps      float64 `json:"mowSpeedMps"`
	GotoSpeedMps     float64 `json:"gotoSpeedMps"`
	FixTimeoutSec    int     `json:"fixTimeoutSec"`
	FinishAndRestart bool    `json:"finishAndRestart"`
	// AbsolutePosition uses Lon/Lat as reference instead of relative positioning.
	AbsolutePosition bool    `json:"absolutePosition"`
	Lon              float64 `json:"lon"`
	Lat              float64 `json:"lat"`
}

// Battery maps voltage to state of charge and tells charging and offline apart.
type Battery struct {
	EmptyV float64 `json:"emptyV"`
	FullV  float64 `json:"fullV"`
	// ChargingBelowA: a docked robot is charging while amps are at or below this.
	ChargingBelowA float64 `json:"chargingBelowA"`
	// OfflineAfterSec without a state report the robot counts as offline.
	OfflineAfterSec int `json:"offlineAfterSec"`
}

// Planner holds the default mow parameters for new tasks.
type Planner struct {
	Pattern  string  `json:"pattern"` // PatternLines, PatternSquares or PatternRings
	WidthM   float64 `json:"widthM"`  // distance between lanes (cutting width)
	AngleDeg float64 `json:"angleDeg"`
	// DistanceToBorder in lane widths, kept free along the perimeter.
	DistanceToBorder int  `json:"distanceToBorder"`
	MowArea          bool `json:"mowArea"`
	BorderLaps       int  `json:"borderLaps"`
	MowExclusions    bool `json:"mowExclusions"` // mow around exclusions
	BorderCCW        bool `json:"borderCcw"`
}

// API is the external MQTT API for home automation (legacy compatible).
type API struct {
	Enabled bool   `json:"enabled"`
	Broker  string `json:"broker"` // tcp://host:1883
	// ServerName is the topic prefix, e.g. "CaSSAndRA".
	ServerName string `json:"serverName"`
	ClientID   string `json:"clientId"`
	User       string `json:"user"`
	Password   string `json:"password"`
}

// Appearance is how the robot is drawn on the map.
type Appearance struct {
	RobotPicture string `json:"robotPicture"` // one of RobotPictures
	// RobotSizeCm is the edge of the square picture on the map, as in legacy CaSSAndRA.
	RobotSizeCm int `json:"robotSizeCm"`
}

// Default returns the settings of a fresh installation: the simulated robot
// and the legacy CaSSAndRA defaults.
func Default() Settings {
	return Settings{
		Connection: Connection{Kind: LinkSim, UARTPort: "/dev/ttyACM0", UARTBaud: 115200, MQTTMower: "Ardumower", MQTTClientID: "CaSSAndRA"},
		Rover:      Rover{MowSpeedMps: 0.25, GotoSpeedMps: 0.3, FixTimeoutSec: 60},
		Battery:    Battery{EmptyV: 22, FullV: 28, ChargingBelowA: -0.03, OfflineAfterSec: 60},
		Planner:    Planner{Pattern: PatternLines, WidthM: 0.18, DistanceToBorder: 1, MowArea: true, BorderLaps: 1, MowExclusions: true},
		API:        API{ServerName: "CaSSAndRA", ClientID: "CaSSAndRA-API"},
		Appearance: Appearance{RobotPicture: "default", RobotSizeCm: 100},
	}
}

// ErrInvalid wraps every validation error.
var ErrInvalid = errors.New("invalid settings")

// Validate checks that the settings can be used as they are.
func (s Settings) Validate() error {
	var errs []string
	check := func(ok bool, format string, args ...any) {
		if !ok {
			errs = append(errs, fmt.Sprintf(format, args...))
		}
	}
	c := s.Connection
	switch c.Kind {
	case LinkSim:
	case LinkHTTP:
		u, err := url.Parse(c.HTTPURL)
		check(err == nil && (u.Scheme == "http" || u.Scheme == "https") && u.Host != "",
			"connection.httpUrl must be a URL like http://192.168.1.50, got %q", c.HTTPURL)
	case LinkUART:
		check(c.UARTPort != "", "connection.uartPort must be set")
		check(c.UARTBaud > 0, "connection.uartBaud must be positive")
	case LinkMQTT:
		u, err := url.Parse(c.MQTTBroker)
		check(err == nil && u.Scheme != "" && u.Host != "",
			"connection.mqttBroker must be a URL like tcp://192.168.1.10:1883, got %q", c.MQTTBroker)
		check(strings.TrimSpace(c.MQTTMower) != "", "connection.mqttMower must be set")
		check(c.MQTTClientID != "", "connection.mqttClientId must be set")
	default:
		check(false, "connection.kind must be sim, http, uart or mqtt, got %q", c.Kind)
	}
	check(c.HTTPPassword >= 0, "connection.httpPassword must not be negative")

	r := s.Rover
	check(between(r.MowSpeedMps, 0.01, 1), "rover.mowSpeedMps must be between 0.01 and 1")
	check(between(r.GotoSpeedMps, 0.01, 1), "rover.gotoSpeedMps must be between 0.01 and 1")
	check(r.FixTimeoutSec >= 0, "rover.fixTimeoutSec must not be negative")
	check(between(r.Lon, -180, 180), "rover.lon must be between -180 and 180")
	check(between(r.Lat, -90, 90), "rover.lat must be between -90 and 90")

	b := s.Battery
	check(between(b.EmptyV, 1, 100) && between(b.FullV, 1, 100) && b.EmptyV < b.FullV,
		"battery.emptyV must be below battery.fullV (both 1..100 V)")
	check(between(b.ChargingBelowA, -10, 0), "battery.chargingBelowA must be between -10 and 0")
	check(b.OfflineAfterSec >= 5, "battery.offlineAfterSec must be at least 5")

	p := s.Planner
	check(p.Pattern == PatternLines || p.Pattern == PatternSquares || p.Pattern == PatternRings,
		"planner.pattern must be lines, squares or rings, got %q", p.Pattern)
	check(between(p.WidthM, 0.01, 1), "planner.widthM must be between 0.01 and 1")
	check(between(p.AngleDeg, 0, 360), "planner.angleDeg must be between 0 and 360")
	check(p.DistanceToBorder >= 0 && p.DistanceToBorder <= 10, "planner.distanceToBorder must be between 0 and 10")
	check(p.BorderLaps >= 0 && p.BorderLaps <= 10, "planner.borderLaps must be between 0 and 10")

	a := s.API
	if a.Enabled {
		u, err := url.Parse(a.Broker)
		check(err == nil && u.Scheme != "" && u.Host != "",
			"api.broker must be a URL like tcp://192.168.1.10:1883, got %q", a.Broker)
		check(strings.TrimSpace(a.ServerName) != "", "api.serverName must be set")
		check(a.ClientID != "", "api.clientId must be set")
	}

	ap := s.Appearance
	check(slices.Contains(RobotPictures, ap.RobotPicture),
		"appearance.robotPicture must be one of %s, got %q", strings.Join(RobotPictures, ", "), ap.RobotPicture)
	check(ap.RobotSizeCm >= 50 && ap.RobotSizeCm <= 500, "appearance.robotSizeCm must be between 50 and 500")

	if len(errs) > 0 {
		return fmt.Errorf("%w: %s", ErrInvalid, strings.Join(errs, "; "))
	}
	return nil
}

// between is false for NaN.
func between(v, lo, hi float64) bool {
	return !math.IsNaN(v) && v >= lo && v <= hi
}
