package app_test

import (
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/stats"
)

func TestTheSimulatorIsRecorded(t *testing.T) {
	cfg := testConfig(t)
	cfg.Poll.StatsInterval = 20 * time.Millisecond
	cfg.Stats = stats.Config{Interval: 20 * time.Millisecond}
	r := startWith(t, cfg)

	deadline := time.Now().Add(5 * time.Second)
	for {
		var got stats.JSON
		err := getJSON(r.baseURL+"/api/stats?points=2000", &got)
		if err == nil && len(got.Samples) > 0 && got.Totals["idleSec"]+got.Totals["chargeSec"] > 0 {
			if got.Samples[0].BatteryV <= 0 || got.Samples[0].Satellites <= 0 {
				t.Errorf("sample = %+v, want battery and satellites", got.Samples[0])
			}
			return
		}
		if time.Now().After(deadline) {
			t.Fatalf("no samples or counters recorded: %+v (%v)", got, err)
		}
		time.Sleep(20 * time.Millisecond)
	}
}
