package link

import (
	"context"
	"errors"
	"fmt"
	"math"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// Simulator errors, as a real Transport would report them.
var (
	ErrSimOffline = errors.New("simulator offline")
	// ErrNoReply is returned for lines the firmware ignores (bad checksum,
	// unknown command, too short).
	ErrNoReply = errors.New("no reply")
)

// SimConfig configures the simulated robot.
type SimConfig struct {
	Start geo.Point
	// Password > 0 makes the robot request encryption, like HTTP with ENABLE_PASS.
	Password int

	BatteryFullV     float64 // charging stops here
	BatteryDockV     float64 // mowing robot docks below this voltage
	DrainVPerSec     float64 // while driving
	ChargeVPerSec    float64 // while charging
	DefaultSpeedMps  float64 // until AT+C sets a speed
	ManualTimeoutSec float64 // AT+M expires after this time without a new one
}

// DefaultSimConfig returns a robot that behaves like an Ardumower on fast forward.
func DefaultSimConfig() SimConfig {
	return SimConfig{
		BatteryFullV:     28.5,
		BatteryDockV:     23,
		DrainVPerSec:     0.001,
		ChargeVPerSec:    0.01,
		DefaultSpeedMps:  0.25,
		ManualTimeoutSec: 2,
	}
}

// Sim is a simulated Sunray robot. It implements Transport, so it runs
// through the same Poller as HTTP and UART. Time only advances in Step, which
// keeps tests deterministic; Run steps in real time for development.
type Sim struct {
	cfg SimConfig

	mu      sync.Mutex
	offline bool
	key     int // encryption key after AT+V, 0 = none

	pos        geo.Point
	heading    float64
	voltage    float64
	op         protocol.Op
	sensor     protocol.Sensor
	mowMotor   bool
	speed      float64
	dockAfter  bool
	manualLin  float64
	manualAng  float64
	manualLeft float64 // seconds until the last AT+M expires

	upload     []geo.Point // AT+W buffer
	exclLens   []int
	perimeter  []geo.Point
	exclusions [][]geo.Point
	dock       []geo.Point
	way        []geo.Point
	wayIdx     int
	dockIdx    int
	target     geo.Point

	idleSec, chargeSec, mowSec float64
	distance                   float64
}

// NewSim returns an idle robot with a full battery at cfg.Start.
func NewSim(cfg SimConfig) *Sim {
	return &Sim{
		cfg:     cfg,
		pos:     cfg.Start,
		voltage: cfg.BatteryFullV,
		speed:   cfg.DefaultSpeedMps,
	}
}

// Run advances the simulation in real time until ctx ends.
func (s *Sim) Run(ctx context.Context, tick time.Duration) {
	t := time.NewTicker(tick)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			s.Step(tick)
		}
	}
}

// SetOffline makes every exchange fail, like an unreachable robot.
func (s *Sim) SetOffline(offline bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.offline = offline
}

// SetBatteryVoltage sets the battery voltage.
func (s *Sim) SetBatteryVoltage(v float64) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.voltage = v
}

// TriggerRain makes a mowing robot dock, like the rain sensor does.
func (s *Sim) TriggerRain() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.op == protocol.OpMow {
		s.sensor = protocol.Sensor(16) // SENS_RAIN
		s.startDock()
	}
}

// State returns what AT+S would report.
func (s *Sim) State() protocol.State {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.stateLocked()
}

// Exchange implements Transport: it answers one framed request line.
func (s *Sim) Exchange(ctx context.Context, line string) (string, error) {
	if err := ctx.Err(); err != nil {
		return "", err
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.offline {
		return "", ErrSimOffline
	}
	line = strings.TrimRight(line, "\r\n")
	if s.key != 0 && !strings.HasPrefix(line, protocol.RequestVersion) {
		line = protocol.Decrypt(line, s.key)
	}
	payload, err := protocol.Unframe(line)
	if err != nil {
		return "", fmt.Errorf("%w: %w", ErrNoReply, err)
	}
	answer, ok := s.handle(payload)
	if !ok {
		return "", fmt.Errorf("%w: %q", ErrNoReply, payload)
	}
	return protocol.Frame(answer) + "\r\n", nil
}

// handle runs one request like Comm::processCmd and returns the answer.
func (s *Sim) handle(payload string) (string, bool) {
	cmd, ok := strings.CutPrefix(payload, "AT+")
	if !ok {
		return "", false
	}
	name, args, _ := strings.Cut(cmd, ",")
	switch name {
	case "V":
		return s.version(), true
	case "S":
		return s.summary(), true
	case "S2":
		return "S2,0", true
	case "T":
		return s.stats(), true
	case "C":
		s.control(numbers(args))
		return "C", true
	case "M":
		v := numbers(args)
		s.manualLin, s.manualAng = at(v, 0), at(v, 1)
		s.manualLeft = s.cfg.ManualTimeoutSec
		return "M", true
	case "W":
		return s.waypoints(numbers(args)), true
	case "N":
		s.wayCount(numbers(args))
		return "N", true
	case "X":
		return s.exclusionCount(numbers(args)), true
	case "P":
		return "P", true
	case "Y", "Y2":
		return name, true
	case "Y3":
		s.offline = true // switched off
		return name, true
	}
	return "", false
}

func (s *Sim) version() string {
	s.key = 0
	challenge := 0
	if s.cfg.Password > 0 {
		// The firmware picks a random challenge whose key is in 1..94; the
		// largest such challenge keeps the simulator deterministic.
		for c := 199; c > 1; c-- {
			if k := s.cfg.Password % c; k >= 1 && k <= 94 {
				challenge, s.key = c, k
				break
			}
		}
	}
	return fmt.Sprintf("V,Sunray,1.0.332,%d,%d,Simulator,SIM,,,cassandra-sim", boolInt(s.key != 0), challenge)
}

func (s *Sim) stateLocked() protocol.State {
	amps := 0.1
	switch {
	case s.op == protocol.OpCharge && s.voltage < s.cfg.BatteryFullV:
		amps = -1.2
	case s.op == protocol.OpCharge:
		amps = -0.01
	case s.mowMotor && s.op == protocol.OpMow:
		amps = 0.7
	}
	return protocol.State{
		BatteryVoltage:   s.voltage,
		X:                s.pos.X,
		Y:                s.pos.Y,
		HeadingRad:       s.heading,
		Solution:         protocol.SolutionFix,
		Op:               s.op,
		MowPointIndex:    s.wayIdx,
		DGPSAgeSec:       0.5,
		Sensor:           s.sensor,
		TargetX:          s.target.X,
		TargetY:          s.target.Y,
		AccuracyM:        0.02,
		Satellites:       30,
		Amps:             amps,
		SatellitesDGPS:   25,
		MapCRC:           s.mapCRC(),
		TimetableWeekday: -1,
	}
}

func (s *Sim) summary() string {
	st := s.stateLocked()
	f := func(v float64) string { return strconv.FormatFloat(v, 'f', 2, 64) }
	return strings.Join([]string{
		"S", f(st.BatteryVoltage), f(st.X), f(st.Y), f(st.HeadingRad),
		strconv.Itoa(int(st.Solution)), strconv.Itoa(int(st.Op)), strconv.Itoa(st.MowPointIndex),
		f(st.DGPSAgeSec), strconv.Itoa(int(st.Sensor)), f(st.TargetX), f(st.TargetY), f(st.AccuracyM),
		strconv.Itoa(st.Satellites), f(st.Amps), strconv.Itoa(st.SatellitesDGPS),
		strconv.FormatInt(st.MapCRC, 10), f(st.LateralErrorM), "-1", "0",
	}, ",")
}

func (s *Sim) stats() string {
	fields := []string{
		"T", strconv.Itoa(int(s.idleSec)), strconv.Itoa(int(s.chargeSec)), strconv.Itoa(int(s.mowSec)),
		"0", strconv.Itoa(int(s.mowSec)), "0", strconv.FormatFloat(s.distance, 'f', 2, 64),
	}
	for range 24 { // remaining counters of a current firmware
		fields = append(fields, "0")
	}
	return strings.Join(fields, ",")
}

// control applies AT+C,mow,op,spd,fixTO,restart,perc,skip,sonar,pwm,height,dock.
func (s *Sim) control(v []float64) {
	if mow := at(v, 0); mow >= 0 {
		s.mowMotor = mow == 1
	}
	if spd := at(v, 2); spd >= 0 {
		s.speed = spd
	}
	if dock := at(v, 10); dock >= 0 {
		s.dockAfter = dock == 1
	}
	if perc := at(v, 5); perc >= 0 && len(s.way) > 0 {
		s.wayIdx = min(int(float64(len(s.way))*perc), len(s.way)-1)
	}
	if skip := at(v, 6); skip > 0 && len(s.way) > 0 {
		s.wayIdx = min(s.wayIdx+1, len(s.way)-1)
	}
	if op := at(v, 1); op >= 0 {
		s.setOp(protocol.Op(op))
	}
}

func (s *Sim) setOp(op protocol.Op) {
	s.sensor = 0
	s.manualLeft = 0
	switch op {
	case protocol.OpMow:
		if len(s.way) == 0 {
			s.fail(protocol.Sensor(11)) // SENS_MAP_NO_ROUTE
			return
		}
		s.op = protocol.OpMow
	case protocol.OpDock:
		s.startDock()
	default:
		s.op = op
	}
}

func (s *Sim) startDock() {
	s.mowMotor = false
	if len(s.dock) == 0 {
		s.fail(protocol.Sensor(11))
		return
	}
	s.op = protocol.OpDock
	s.dockIdx = 0
}

func (s *Sim) fail(sensor protocol.Sensor) {
	s.op = protocol.OpError
	s.sensor = sensor
	s.mowMotor = false
}

func (s *Sim) waypoints(v []float64) string {
	if len(v) == 0 {
		return "W,0"
	}
	idx := int(v[0])
	for i := 1; i+1 < len(v); i += 2 {
		for len(s.upload) <= idx {
			s.upload = append(s.upload, geo.Point{})
		}
		s.upload[idx] = geo.Point{X: v[i], Y: v[i+1]}
		idx++
	}
	return "W," + strconv.Itoa(idx)
}

func (s *Sim) exclusionCount(v []float64) string {
	if len(v) == 0 {
		return "X,0"
	}
	idx := int(v[0])
	for _, n := range v[1:] {
		for len(s.exclLens) <= idx {
			s.exclLens = append(s.exclLens, 0)
		}
		s.exclLens[idx] = int(n)
		idx++
	}
	s.splitExclusions()
	return "X," + strconv.Itoa(idx)
}

// wayCount splits the uploaded points into sections (AT+N,peri,excl,dock,mow,free).
func (s *Sim) wayCount(v []float64) {
	counts := [4]int{int(at(v, 0)), int(at(v, 1)), int(at(v, 2)), int(at(v, 3))}
	sections := make([][]geo.Point, 4)
	i := 0
	for n, c := range counts {
		end := min(i+max(c, 0), len(s.upload))
		sections[n] = append([]geo.Point(nil), s.upload[i:end]...)
		i = end
	}
	s.perimeter, s.dock, s.way = sections[0], sections[2], sections[3]
	s.exclusions = [][]geo.Point{sections[1]}
	s.exclLens = nil
	s.wayIdx, s.dockIdx = 0, 0
	s.upload = nil
}

func (s *Sim) splitExclusions() {
	var all []geo.Point
	for _, ex := range s.exclusions {
		all = append(all, ex...)
	}
	s.exclusions = nil
	for _, n := range s.exclLens {
		n = min(n, len(all))
		s.exclusions = append(s.exclusions, all[:n])
		all = all[n:]
	}
}

// mapCRC is what Sunray on Linux reports for the stored map.
func (s *Sim) mapCRC() int64 {
	m := protocol.Map{Perimeter: s.perimeter, Exclusions: s.exclusions, Dock: s.dock, Way: s.way}
	return protocol.MapChecksum(m).Linux
}

// Step advances the simulation by dt.
func (s *Sim) Step(dt time.Duration) {
	s.mu.Lock()
	defer s.mu.Unlock()
	sec := dt.Seconds()
	switch s.op {
	case protocol.OpMow:
		s.mowSec += sec
		s.drain(sec)
		if s.op == protocol.OpMow && s.follow(s.way, &s.wayIdx, sec) {
			s.wayIdx = 0 // like Map::nextMowPoint after the last point
			if s.dockAfter {
				s.startDock()
			} else {
				s.op = protocol.OpIdle
				s.mowMotor = false
			}
		}
	case protocol.OpDock:
		s.drain(sec)
		if s.follow(s.dock, &s.dockIdx, sec) {
			s.op = protocol.OpCharge
		}
	case protocol.OpCharge:
		s.chargeSec += sec
		s.voltage = math.Min(s.cfg.BatteryFullV, s.voltage+s.cfg.ChargeVPerSec*sec)
	case protocol.OpIdle:
		s.idleSec += sec
		s.manual(sec)
	}
}

func (s *Sim) drain(sec float64) {
	s.voltage -= s.cfg.DrainVPerSec * sec
	if s.op == protocol.OpMow && s.voltage < s.cfg.BatteryDockV {
		s.startDock()
	}
}

// follow drives along pts starting at *idx and reports whether the last
// point was reached.
func (s *Sim) follow(pts []geo.Point, idx *int, sec float64) bool {
	budget := s.speed * sec
	for *idx < len(pts) {
		s.target = pts[*idx]
		dx, dy := s.target.X-s.pos.X, s.target.Y-s.pos.Y
		dist := math.Hypot(dx, dy)
		if dist > 0 {
			s.heading = math.Atan2(dy, dx)
		}
		if dist > budget {
			s.pos.X += dx / dist * budget
			s.pos.Y += dy / dist * budget
			s.distance += budget
			return false
		}
		s.pos = s.target
		s.distance += dist
		budget -= dist
		*idx++
	}
	return true
}

func (s *Sim) manual(sec float64) {
	if s.manualLeft <= 0 {
		return
	}
	sec = math.Min(sec, s.manualLeft)
	s.manualLeft -= sec
	s.heading += s.manualAng * sec
	s.pos.X += math.Cos(s.heading) * s.manualLin * sec
	s.pos.Y += math.Sin(s.heading) * s.manualLin * sec
	s.distance += math.Abs(s.manualLin * sec)
}

// numbers parses comma separated values the way the firmware does with
// String::toFloat: invalid values become 0.
func numbers(args string) []float64 {
	if args == "" {
		return nil
	}
	parts := strings.Split(args, ",")
	v := make([]float64, len(parts))
	for i, p := range parts {
		v[i], _ = strconv.ParseFloat(p, 64)
	}
	return v
}

// at returns v[i], or -1 ("unchanged") if the field is missing.
func at(v []float64, i int) float64 {
	if i < len(v) {
		return v[i]
	}
	return -1
}

func boolInt(b bool) int {
	if b {
		return 1
	}
	return 0
}
