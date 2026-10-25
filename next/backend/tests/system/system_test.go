package system_test

import (
	"math"
	"testing"
	"testing/fstest"

	"github.com/EinEinfach/CaSSAndRA/next/backend/system"
)

const stat1 = `cpu  100 0 100 700 100 0 0 0 0 0
cpu0 50 0 50 350 50 0 0 0 0 0
intr 12345
`

const stat2 = `cpu  300 0 300 1300 100 0 0 0 0 0
cpu0 100 0 100 650 50 0 0 0 0 0
`

const meminfo = `MemTotal:        4000000 kB
MemFree:          500000 kB
MemAvailable:    3000000 kB
`

func TestParseStat(t *testing.T) {
	idle, total, ok := system.ParseStat(stat1)
	if !ok || idle != 800 || total != 1000 {
		t.Errorf("ParseStat = %d, %d, %v; want idle+iowait 800 of 1000", idle, total, ok)
	}
	if _, _, ok := system.ParseStat("intr 1\n"); ok {
		t.Error("no cpu line, still ok")
	}
}

func TestParseMeminfo(t *testing.T) {
	if v, ok := system.ParseMeminfo(meminfo); !ok || v != 25 {
		t.Errorf("ParseMeminfo = %v, %v; want 25 %%", v, ok)
	}
	if _, ok := system.ParseMeminfo("nothing"); ok {
		t.Error("empty meminfo, still ok")
	}
}

func TestMonitor(t *testing.T) {
	root := fstest.MapFS{
		"proc/stat":                            {Data: []byte(stat1)},
		"proc/meminfo":                         {Data: []byte(meminfo)},
		"sys/class/thermal/thermal_zone0/temp": {Data: []byte("48312\n")},
	}
	m := system.NewMonitor(root, t.TempDir())
	first := m.Read()
	if first.CPULoadPercent != nil {
		t.Errorf("first CPU load = %v, want none (no previous reading)", *first.CPULoadPercent)
	}
	if first.CPUTempC == nil || math.Abs(*first.CPUTempC-48.312) > 1e-9 {
		t.Errorf("temperature = %v", first.CPUTempC)
	}
	if first.MemUsedPercent == nil || *first.MemUsedPercent != 25 {
		t.Errorf("memory = %v", first.MemUsedPercent)
	}
	if first.DiskUsedPercent == nil || *first.DiskUsedPercent < 0 || *first.DiskUsedPercent > 100 {
		t.Errorf("disk = %v", first.DiskUsedPercent)
	}
	root["proc/stat"] = &fstest.MapFile{Data: []byte(stat2)}
	// 1000 jiffies more, 600 of them idle: 40 % busy
	if got := m.Read().CPULoadPercent; got == nil || math.Abs(*got-40) > 1e-9 {
		t.Errorf("CPU load = %v, want 40", deref(got))
	}
}

func TestMonitorWithoutLinuxFiles(t *testing.T) {
	info := system.NewMonitor(fstest.MapFS{}, "").Read()
	if info.CPULoadPercent != nil || info.CPUTempC != nil || info.MemUsedPercent != nil || info.DiskUsedPercent != nil {
		t.Errorf("info = %+v, want everything unknown", info)
	}
}

func deref(p *float64) any {
	if p == nil {
		return nil
	}
	return *p
}
