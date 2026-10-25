package stats_test

import (
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
	"github.com/EinEinfach/CaSSAndRA/next/backend/stats"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func TestRecorderSamplesOnlyFreshReports(t *testing.T) {
	s, _ := open(t)
	clock := testkit.NewFakeClock(t0)
	r := &fakeRobot{}
	rec := stats.NewRecorder(s, r, stats.Config{Now: clock.Now})

	rec.Record(ctx) // nothing reported yet
	r.set(func(sn *robot.Snapshot) {
		sn.Online, sn.UpdatedAt = true, clock.Now()
		sn.BatteryV, sn.Amps, sn.Satellites, sn.AccuracyM, sn.LateralErrorM = 27.5, -1.2, 31, 0.02, 0.04
	})
	clock.Advance(time.Minute)
	rec.Record(ctx)
	clock.Advance(5 * time.Minute) // the last report is old now
	rec.Record(ctx)
	r.set(func(sn *robot.Snapshot) { sn.Online, sn.UpdatedAt = false, clock.Now() })
	clock.Advance(time.Minute)
	rec.Record(ctx)

	got, err := s.Samples(ctx, t0, t0.Add(time.Hour), 1000)
	if err != nil {
		t.Fatal(err)
	}
	want := stats.Sample{BatteryV: 27.5, Amps: -1.2, Satellites: 31, AccuracyM: 0.02, LateralErrorM: 0.04}
	if len(got) != 1 || !got[0].T.Equal(t0.Add(time.Minute)) {
		t.Fatalf("samples = %+v, want one at the minute with a fresh report", got)
	}
	got[0].T = time.Time{}
	if got[0] != want {
		t.Errorf("sample = %+v, want %+v", got[0], want)
	}
}

func TestRecorderWritesEachCounterReportOnce(t *testing.T) {
	s, _ := open(t)
	clock := testkit.NewFakeClock(t0)
	r := &fakeRobot{}
	rec := stats.NewRecorder(s, r, stats.Config{Now: clock.Now})
	report := func(mowSec int) {
		r.set(func(sn *robot.Snapshot) { sn.Stats, sn.StatsAt = protocol.Stats{DurationMowSec: mowSec}, clock.Now() })
	}
	report(100)
	rec.Record(ctx) // the starting point
	clock.Advance(time.Minute)
	report(160)
	rec.Record(ctx)
	clock.Advance(time.Minute)
	rec.Record(ctx) // no new report: counted once
	clock.Advance(time.Minute)
	rec.Record(ctx)

	got, _ := s.Totals(ctx, t0, t0.Add(time.Hour))
	if got["mowSec"] != 60 {
		t.Errorf("mowSec = %v, want 60", got["mowSec"])
	}
}

func TestRecorderPrunesOldSamples(t *testing.T) {
	s, _ := open(t)
	if err := s.AddSample(ctx, stats.Sample{T: t0}); err != nil {
		t.Fatal(err)
	}
	clock := testkit.NewFakeClock(t0.Add(48 * time.Hour))
	rec := stats.NewRecorder(s, &fakeRobot{}, stats.Config{Now: clock.Now, Retention: 24 * time.Hour})
	rec.Record(ctx)
	if got, _ := s.Samples(ctx, t0.Add(-time.Hour), clock.Now(), 10); len(got) != 0 {
		t.Errorf("samples older than the retention: %+v", got)
	}
}
