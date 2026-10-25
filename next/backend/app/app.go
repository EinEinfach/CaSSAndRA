// Package app wires all features together and runs CaSSAndRA.
package app

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"log/slog"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/mqttapi"
	"github.com/EinEinfach/CaSSAndRA/next/backend/planner"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/schedule"
	"github.com/EinEinfach/CaSSAndRA/next/backend/server"
	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
	"github.com/EinEinfach/CaSSAndRA/next/backend/stats"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

const (
	shutdownTimeout = 5 * time.Second
	// positionModeTimeout bounds sending a changed position mode.
	positionModeTimeout = 5 * time.Second
)

// Config holds everything the app needs to start. The user settings
// (connection, rover, ...) live in DataDir and are changed in the UI.
type Config struct {
	Version string
	UI      fs.FS
	Logger  *slog.Logger
	// DataDir holds settings and maps. On the first start, legacy CaSSAndRA
	// data in the same directory (user/, map/) is imported.
	DataDir string
	// Robot holds the robot defaults; the user settings replace its Settings.
	Robot robot.Config
	// SimTick is the simulation step of the simulated robot.
	SimTick time.Duration
	// Poll controls how often the robot is asked for data.
	Poll link.PollConfig
	// PublishInterval is how often the browser gets state updates (if changed).
	PublishInterval time.Duration
	// Heartbeat keeps idle event streams open through proxies.
	Heartbeat time.Duration
	// Planner computes routes; nil = the C++ planner (if built in).
	Planner tasks.Planner
	// Schedule sets the clock and interval of the schedule (defaults: wall
	// clock, one minute).
	Schedule schedule.Config
	// Stats sets the clock and interval of the statistics (defaults: wall
	// clock, one sample per minute).
	Stats stats.Config
}

// DefaultConfig returns the defaults; only DataDir must be set.
func DefaultConfig() Config {
	return Config{
		Robot:           robot.DefaultConfig(),
		SimTick:         100 * time.Millisecond,
		Poll:            link.DefaultPollConfig(),
		PublishInterval: 200 * time.Millisecond,
		Heartbeat:       15 * time.Second,
	}
}

// validate rejects settings that would make loops spin or panic.
func (c Config) validate() error {
	for name, d := range map[string]time.Duration{
		"SimTick": c.SimTick, "Poll.StateInterval": c.Poll.StateInterval,
		"Poll.ObstaclesInterval": c.Poll.ObstaclesInterval, "Poll.StatsInterval": c.Poll.StatsInterval,
		"Poll.ReconnectDelay": c.Poll.ReconnectDelay, "PublishInterval": c.PublishInterval,
		"Heartbeat": c.Heartbeat, "Robot.MapCRCTimeout": c.Robot.MapCRCTimeout,
	} {
		if d <= 0 {
			return fmt.Errorf("invalid config: %s must be positive, got %v (start from DefaultConfig)", name, d)
		}
	}
	if c.DataDir == "" {
		return errors.New("invalid config: DataDir must be set")
	}
	return nil
}

// Run serves CaSSAndRA on ln until ctx is cancelled, then shuts down gracefully.
func Run(ctx context.Context, cfg Config, ln net.Listener) error {
	if err := cfg.validate(); err != nil {
		return err
	}
	if cfg.Logger == nil {
		cfg.Logger = slog.New(slog.DiscardHandler)
	}
	log := cfg.Logger

	data, err := openData(cfg.DataDir, log)
	if err != nil {
		return err
	}
	settingsStore, mapStore, taskStore, scheduleStore := data.settings, data.maps, data.tasks, data.schedule
	statsStore, err := stats.Open(filepath.Join(cfg.DataDir, "stats.db"))
	if err != nil {
		return err
	}
	// Registered first, so it runs after the goroutines have stopped.
	defer func() {
		if err := statsStore.Close(); err != nil {
			log.Warn("close stats", "err", err)
		}
	}()

	// Deferred in reverse: cancel the background goroutines, then wait for them.
	var wg sync.WaitGroup
	defer wg.Wait()
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	goroutine := func(f func()) {
		wg.Add(1)
		go func() {
			defer wg.Done()
			f()
		}()
	}

	sender := &switchSender{}
	robotCfg := cfg.Robot
	robotCfg.Settings = robotSettings(settingsStore.Get())
	robotCfg.Logger = log.With("feature", "robot")
	r := robot.New(sender, robotCfg)
	hub := server.NewHub(cfg.Heartbeat)

	// The browser follows the settings it shows everywhere (e.g. the robot picture).
	publishSettings := func(s settings.Settings) {
		if b, err := json.Marshal(settings.ViewOf(s)); err == nil {
			hub.Publish("settings", b)
		}
	}
	publishSettings(settingsStore.Get())

	reconnect := make(chan struct{}, 1)
	apiChanged := make(chan struct{}, 1)
	settingsStore.OnChange(func(old, next settings.Settings) {
		publishSettings(next)
		r.SetSettings(robotSettings(next))
		if old.Rover.AbsolutePosition != next.Rover.AbsolutePosition || old.Rover.Lon != next.Rover.Lon || old.Rover.Lat != next.Rover.Lat {
			pctx, cancel := context.WithTimeout(ctx, positionModeTimeout)
			if err := r.SendPositionMode(pctx); err != nil && !errors.Is(err, link.ErrOffline) {
				log.Warn("send changed position mode", "err", err)
			}
			cancel()
		}
		if old.Connection != next.Connection {
			select {
			case reconnect <- struct{}{}:
			default: // a reconnect is pending anyway
			}
		}
		if old.API != next.API {
			select {
			case apiChanged <- struct{}{}:
			default:
			}
		}
	})
	publishMaps := func() {
		if b, err := json.Marshal(mapStore.ListJSON()); err == nil {
			hub.Publish("maps", b)
		}
	}
	publishMaps()

	if cfg.Planner == nil {
		cfg.Planner = planner.New()
	}
	taskService := tasks.New(cfg.Planner, mapStore, r, taskStore, tasks.Config{})
	publishTasks := func() {
		if b, err := json.Marshal(taskService.ListJSON()); err == nil {
			hub.Publish("tasks", b)
		}
	}
	publishTasks()
	taskStore.OnChange(publishTasks)
	taskStore.OnChange(func() {
		exists := func(id string) bool { _, err := taskStore.Get(id); return err == nil }
		if err := scheduleStore.KeepTasks(exists); err != nil {
			log.Warn("remove deleted tasks from the schedule", "err", err)
		}
	})
	publishPlan := func(*tasks.Plan) {
		if b, err := json.Marshal(taskService.PlanJSON()); err == nil {
			hub.Publish("plan", b)
		}
	}
	publishPlan(nil)
	taskService.OnChange(publishPlan)
	mapStore.OnChange(func() {
		publishMaps()
		taskService.MapsChanged()
		exists := func(id string) bool { _, err := mapStore.Get(id); return err == nil }
		if err := taskStore.KeepMaps(exists); err != nil {
			log.Warn("remove tasks of a deleted map", "err", err)
		}
	})

	// The simulated robot starts with the active map, so the live view and the
	// planning show the same garden; the demo garden only without a map.
	simMap := func() protocol.Map {
		if m, err := mapStore.Get(mapStore.ActiveID()); err == nil {
			return m.Robot(nil)
		}
		return link.DemoMap()
	}
	scheduleCfg := cfg.Schedule
	scheduleCfg.Logger = log
	runner := schedule.NewRunner(scheduleStore, r, taskService, taskStore, scheduleCfg)
	publishSchedule := func() {
		if b, err := json.Marshal(runner.JSON()); err == nil {
			hub.Publish("schedule", b)
		}
	}
	publishSchedule()
	scheduleStore.OnChange(publishSchedule)
	runner.OnChange(publishSchedule)
	goroutine(func() { runner.Run(ctx) })

	statsCfg := cfg.Stats
	statsCfg.Logger = log
	recorder := stats.NewRecorder(statsStore, r, statsCfg)
	goroutine(func() { recorder.Run(ctx) })

	api := mqttapi.New(mqttapi.Deps{
		Robot: r, Tasks: taskService, Maps: mapStore, Saved: taskStore, Schedule: scheduleStore,
		Defaults: tasks.Parameters(settingsStore.Get().Planner),
	}, mqttapi.Config{Version: cfg.Version, Logger: log.With("feature", "mqttapi")})
	goroutine(func() { superviseAPI(ctx, api, settingsStore, apiChanged, log.With("feature", "mqttapi")) })

	goroutine(func() { superviseLink(ctx, cfg, settingsStore, r, sender, reconnect, simMap) })
	goroutine(func() { r.PublishState(ctx, cfg.PublishInterval, func(b []byte) { hub.Publish("robot", b) }) })

	mapsAPI := mapStore.Handler(r)
	tasksAPI := taskService.Handler()
	srv := &http.Server{
		Handler: server.New(server.Options{
			Version: cfg.Version,
			UI:      cfg.UI,
			Logger:  log,
			Events:  hub,
			Routes: map[string]http.Handler{
				"/api/robot/":   r.Handler(),
				"/api/settings": settingsStore.Handler(),
				"/api/maps":     mapsAPI,
				"/api/maps/":    mapsAPI,
				"/api/tasks":    tasksAPI,
				"/api/tasks/":   tasksAPI,
				"/api/schedule": runner.Handler(),
				"/api/stats":    statsStore.Handler(cfg.Stats.Now),
			},
		}),
		ReadHeaderTimeout: 5 * time.Second,
		// Requests end with the app, so open event streams do not block shutdown.
		BaseContext: func(net.Listener) context.Context { return ctx },
	}

	serveErr := make(chan error, 1)
	go func() { serveErr <- srv.Serve(ln) }()
	log.Info("CaSSAndRA started", "addr", ln.Addr().String(), "version", cfg.Version, "data", cfg.DataDir)

	select {
	case err := <-serveErr:
		return fmt.Errorf("serve http: %w", err)
	case <-ctx.Done():
	}

	log.Info("shutting down")
	shutdownCtx, cancelShutdown := context.WithTimeout(context.WithoutCancel(ctx), shutdownTimeout)
	defer cancelShutdown()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("shutdown http: %w", err)
	}
	if err := <-serveErr; !errors.Is(err, http.ErrServerClosed) {
		return fmt.Errorf("serve http: %w", err)
	}
	return nil
}

// stores are the files of the data directory.
type stores struct {
	settings *settings.Store
	maps     *maps.Store
	tasks    *tasks.Store
	schedule *schedule.Store
}

// openData opens settings, maps and tasks. On the first start it imports the
// data of legacy CaSSAndRA from the same directory.
func openData(dir string, log *slog.Logger) (stores, error) {
	settingsStore, err := settings.Open(filepath.Join(dir, "settings.json"))
	if err != nil {
		return stores{}, err
	}
	if !settingsStore.Exists() {
		s, found, warnings, err := settings.ImportLegacy(filepath.Join(dir, "user"))
		if err != nil {
			return stores{}, err
		}
		for _, w := range warnings {
			log.Warn("legacy settings import", "problem", w)
		}
		if err := settingsStore.Set(s); err != nil {
			return stores{}, err
		}
		log.Info("settings created", "importedFromLegacy", found)
	}

	mapStore, err := maps.OpenStore(filepath.Join(dir, "maps"), maps.StoreConfig{})
	if err != nil {
		return stores{}, err
	}
	if mapStore.Fresh() {
		li, err := maps.ImportLegacy(filepath.Join(dir, "map"))
		if err != nil {
			log.Warn("legacy maps import", "err", err)
		}
		n, warnings := mapStore.Import(li)
		for _, w := range warnings {
			log.Warn("legacy maps import", "problem", w)
		}
		if n > 0 {
			log.Info("legacy maps imported", "maps", n, "active", li.Active)
		}
	}
	taskStore, err := tasks.OpenStore(filepath.Join(dir, "tasks.json"), tasks.StoreConfig{})
	if err != nil {
		return stores{}, err
	}
	if !taskStore.Exists() {
		mapIDs := map[string]string{}
		for _, m := range mapStore.List() {
			mapIDs[m.Name] = m.ID
		}
		li, err := tasks.ImportLegacy(filepath.Join(dir, "map"), mapIDs)
		if err != nil {
			log.Warn("legacy tasks import", "err", err)
		}
		n, warnings := taskStore.Import(li)
		for _, w := range warnings {
			log.Warn("legacy tasks import", "problem", w)
		}
		if n > 0 {
			log.Info("legacy tasks imported", "tasks", n)
		}
	}
	scheduleStore, err := schedule.OpenStore(filepath.Join(dir, "schedule.json"))
	if err != nil {
		return stores{}, err
	}
	if legacy := filepath.Join(dir, "user", "schedulecfg.json"); !scheduleStore.Exists() && fileExists(legacy) {
		importSchedule(scheduleStore, taskStore, mapStore.ActiveID(), legacy, log)
	}
	return stores{settings: settingsStore, maps: mapStore, tasks: taskStore, schedule: scheduleStore}, nil
}

// importSchedule imports the legacy schedule, whose task names refer to the
// map that was active. It is imported switched off: the robot should not
// start mowing on its own just because the new app was started.
func importSchedule(store *schedule.Store, taskStore *tasks.Store, activeMap, path string, log *slog.Logger) {
	li, err := schedule.ImportLegacy(path, func(name string) (string, bool) {
		for _, t := range taskStore.List() {
			if t.MapID == activeMap && t.Name == name {
				return t.ID, true
			}
		}
		return "", false
	})
	if err != nil {
		log.Warn("legacy schedule import", "err", err)
		li.Schedule = schedule.Default()
	}
	for _, w := range li.Warnings {
		log.Warn("legacy schedule import", "problem", w)
	}
	wasActive := li.Schedule.Active
	li.Schedule.Active = false
	if err := store.Set(li.Schedule); err != nil {
		log.Warn("legacy schedule import", "err", err)
		return
	}
	log.Info("legacy schedule imported, switched off", "wasActive", wasActive)
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

func robotSettings(s settings.Settings) robot.Settings {
	return robot.Settings{
		MowSpeedMps:      s.Rover.MowSpeedMps,
		GotoSpeedMps:     s.Rover.GotoSpeedMps,
		FixTimeoutSec:    s.Rover.FixTimeoutSec,
		FinishAndRestart: s.Rover.FinishAndRestart,
		AbsolutePosition: s.Rover.AbsolutePosition,
		Lon:              s.Rover.Lon,
		Lat:              s.Rover.Lat,
		BatteryEmptyV:    s.Battery.EmptyV,
		BatteryFullV:     s.Battery.FullV,
		ChargingBelowA:   s.Battery.ChargingBelowA,
		OfflineAfter:     time.Duration(s.Battery.OfflineAfterSec) * time.Second,
	}
}
