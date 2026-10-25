package stats_test

import (
	"context"
	"database/sql"
	"math"
	"os"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/stats"

	_ "modernc.org/sqlite"
)

var ctx = context.Background()

func TestOpenCreatesAPrivateFileAndKeepsData(t *testing.T) {
	s, path := open(t)
	if info, err := os.Stat(path); err != nil || info.Mode().Perm() != 0o600 {
		t.Errorf("file mode = %v (%v), want 0600", info.Mode().Perm(), err)
	}
	if err := s.AddSample(ctx, stats.Sample{T: t0, BatteryV: 27}); err != nil {
		t.Fatal(err)
	}
	if err := s.Close(); err != nil {
		t.Fatal(err)
	}
	again, err := stats.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = again.Close() }()
	got, err := again.Samples(ctx, t0, t0.Add(time.Hour), 10)
	if err != nil || len(got) != 1 || got[0].BatteryV != 27 {
		t.Errorf("after reopening: %+v (%v)", got, err)
	}
}

func TestOpenRefusesForeignFiles(t *testing.T) {
	t.Run("not a database", func(t *testing.T) {
		path := t.TempDir() + "/stats.db"
		if err := os.WriteFile(path, []byte("this is not sqlite, just some text that is long enough"), 0o600); err != nil {
			t.Fatal(err)
		}
		if s, err := stats.Open(path); err == nil {
			_ = s.Close()
			t.Error("opened a text file")
		}
	})
	t.Run("a newer schema", func(t *testing.T) {
		_, path := open(t)
		db, err := sql.Open("sqlite", path)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := db.Exec("PRAGMA user_version = 99"); err != nil {
			t.Fatal(err)
		}
		_ = db.Close()
		if s, err := stats.Open(path); err == nil {
			_ = s.Close()
			t.Error("opened a database with an unknown schema")
		}
	})
}

func TestSamplesAreAveragedPerBucket(t *testing.T) {
	s, _ := open(t)
	for m := range 10 {
		if err := s.AddSample(ctx, stats.Sample{
			T: t0.Add(time.Duration(m) * time.Minute), BatteryV: 20 + float64(m), Amps: 1, Satellites: 30,
		}); err != nil {
			t.Fatal(err)
		}
	}
	all, err := s.Samples(ctx, t0, t0.Add(10*time.Minute), 100)
	if err != nil || len(all) != 10 {
		t.Fatalf("one bucket per minute: %d samples (%v), want 10", len(all), err)
	}
	two, _ := s.Samples(ctx, t0, t0.Add(10*time.Minute), 2)
	if len(two) != 2 || two[0].BatteryV != 22 || two[1].BatteryV != 27 || !two[1].T.Equal(t0.Add(5*time.Minute)) {
		t.Errorf("two buckets = %+v, want averages 22 and 27", two)
	}
	end, _ := s.Samples(ctx, t0, t0.Add(3*time.Minute), 100)
	if len(end) != 3 {
		t.Errorf("the end is exclusive: %d samples, want 3", len(end))
	}
	none, err := s.Samples(ctx, t0.Add(time.Hour), t0.Add(2*time.Hour), 100)
	if err != nil || none == nil || len(none) != 0 {
		t.Errorf("empty range = %#v (%v), want an empty list", none, err)
	}
}

func TestStatsCountTheGrowthPerHour(t *testing.T) {
	s, path := open(t)
	report := func(at time.Duration, st protocol.Stats) {
		t.Helper()
		if err := s.AddStats(ctx, t0.Add(at), st); err != nil {
			t.Fatal(err)
		}
	}
	report(0, protocol.Stats{DurationMowSec: 1000, Obstacles: 5, DistanceMowTraveledM: 100, MaxCycleTimeSec: 0.2})
	totals, _ := s.Totals(ctx, t0, t0.Add(24*time.Hour))
	if totals["mowSec"] != 0 || totals["obstacles"] != 0 {
		t.Fatalf("the first report only sets the start: %v", totals)
	}

	report(10*time.Minute, protocol.Stats{DurationMowSec: 1600, Obstacles: 7, DistanceMowTraveledM: 160.5, MaxCycleTimeSec: 0.5})
	report(50*time.Minute, protocol.Stats{DurationMowSec: 2000, Obstacles: 7, DistanceMowTraveledM: 200, MaxCycleTimeSec: 0.3})
	// The robot restarted: its counters start from zero again.
	report(70*time.Minute, protocol.Stats{DurationMowSec: 300, Obstacles: 1, DistanceMowTraveledM: 10, MaxCycleTimeSec: 0.1})

	tests := []struct {
		name     string
		from, to time.Time
		want     map[string]float64
	}{
		{"both hours", t0, t0.Add(2 * time.Hour), map[string]float64{
			"mowSec": 1300, "obstacles": 3, "distanceMowM": 110, "maxCycleTimeSec": 0.5,
		}},
		{"the first hour", t0, t0.Add(time.Hour), map[string]float64{
			"mowSec": 1000, "obstacles": 2, "distanceMowM": 100, "maxCycleTimeSec": 0.5,
		}},
		{"from within the second hour", t0.Add(80 * time.Minute), t0.Add(2 * time.Hour), map[string]float64{
			"mowSec": 300, "obstacles": 1, "distanceMowM": 10, "maxCycleTimeSec": 0.1,
		}},
		{"nothing recorded", t0.Add(-48 * time.Hour), t0.Add(-24 * time.Hour), map[string]float64{
			"mowSec": 0, "maxCycleTimeSec": 0,
		}},
	}
	for _, tt := range tests {
		got, err := s.Totals(ctx, tt.from, tt.to)
		if err != nil {
			t.Fatal(err)
		}
		for k, v := range tt.want {
			if math.Abs(got[k]-v) > 1e-9 {
				t.Errorf("%s: %s = %v, want %v", tt.name, k, got[k], v)
			}
		}
	}

	// The starting point survives a restart of the app.
	_ = s.Close()
	again, err := stats.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = again.Close() }()
	if err := again.AddStats(ctx, t0.Add(3*time.Hour), protocol.Stats{DurationMowSec: 400}); err != nil {
		t.Fatal(err)
	}
	got, _ := again.Totals(ctx, t0.Add(3*time.Hour), t0.Add(4*time.Hour))
	if got["mowSec"] != 100 {
		t.Errorf("after reopening mowSec = %v, want 100", got["mowSec"])
	}
}

func TestTotalsNameEveryCounter(t *testing.T) {
	s, _ := open(t)
	got, err := s.Totals(ctx, t0, t0.Add(time.Hour))
	if err != nil {
		t.Fatal(err)
	}
	for _, k := range []string{"idleSec", "chargeSec", "mowSec", "mowFixSec", "mowFloatSec", "mowInvalidSec",
		"distanceMowM", "obstacles", "bumper", "gpsJumps", "maxDgpsAgeSec", "gpsChecksumErrors"} {
		if _, ok := got[k]; !ok {
			t.Errorf("totals miss %q", k)
		}
	}
}

func TestPruneKeepsRecentSamples(t *testing.T) {
	s, _ := open(t)
	for _, at := range []time.Duration{0, 2 * time.Hour} {
		if err := s.AddSample(ctx, stats.Sample{T: t0.Add(at)}); err != nil {
			t.Fatal(err)
		}
	}
	if err := s.Prune(ctx, t0.Add(time.Hour)); err != nil {
		t.Fatal(err)
	}
	got, _ := s.Samples(ctx, t0.Add(-time.Hour), t0.Add(3*time.Hour), 100)
	if len(got) != 1 || !got[0].T.Equal(t0.Add(2*time.Hour)) {
		t.Errorf("after pruning: %+v", got)
	}
}
