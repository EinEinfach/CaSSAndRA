// Package system reports the load of the computer CaSSAndRA runs on (CPU,
// temperature, memory, disk) and shuts it down on request.
package system

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io/fs"
	"math"
	"net/http"
	"os/exec"
	"strconv"
	"strings"
	"sync"
	"syscall"
)

// Info is one reading; nil means unknown on this system.
type Info struct {
	CPULoadPercent  *float64
	CPUTempC        *float64
	MemUsedPercent  *float64
	DiskUsedPercent *float64
}

// Monitor reads Info from /proc and /sys (Linux). Safe for concurrent use.
type Monitor struct {
	root     fs.FS  // the file system root, "/" in production
	diskPath string // the disk to report, e.g. the data directory

	mu          sync.Mutex
	idle, total uint64 // of the previous /proc/stat reading
}

// NewMonitor reads below root (os.DirFS("/")) and reports the disk of diskPath.
func NewMonitor(root fs.FS, diskPath string) *Monitor {
	return &Monitor{root: root, diskPath: diskPath}
}

// Read returns the current values. The CPU load is the share since the
// previous Read; the first one has none.
func (m *Monitor) Read() Info {
	var info Info
	if b, err := fs.ReadFile(m.root, "proc/stat"); err == nil {
		if idle, total, ok := ParseStat(string(b)); ok {
			m.mu.Lock()
			if total > m.total && m.total > 0 {
				v := 100 * (1 - float64(idle-m.idle)/float64(total-m.total))
				info.CPULoadPercent = &v
			}
			m.idle, m.total = idle, total
			m.mu.Unlock()
		}
	}
	if b, err := fs.ReadFile(m.root, "sys/class/thermal/thermal_zone0/temp"); err == nil {
		if v, err := strconv.ParseFloat(strings.TrimSpace(string(b)), 64); err == nil {
			c := v / 1000
			info.CPUTempC = &c
		}
	}
	if b, err := fs.ReadFile(m.root, "proc/meminfo"); err == nil {
		if v, ok := ParseMeminfo(string(b)); ok {
			info.MemUsedPercent = &v
		}
	}
	if m.diskPath != "" {
		var st syscall.Statfs_t
		if err := syscall.Statfs(m.diskPath, &st); err == nil && st.Blocks > 0 {
			v := 100 * (1 - float64(st.Bavail)/float64(st.Blocks))
			info.DiskUsedPercent = &v
		}
	}
	return info
}

// InfoJSON is the response of GET /api/system; null = unknown here
// (e.g. no temperature sensor, or not Linux).
type InfoJSON struct {
	CPULoadPercent  *float64 `json:"cpuLoadPercent"`
	CPUTempC        *float64 `json:"cpuTempC"`
	MemUsedPercent  *float64 `json:"memUsedPercent"`
	DiskUsedPercent *float64 `json:"diskUsedPercent"`
}

// Handler serves GET /api/system with a fresh reading, rounded to one decimal.
func (m *Monitor) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/system", func(w http.ResponseWriter, _ *http.Request) {
		info := m.Read()
		body := InfoJSON{
			CPULoadPercent:  round1(info.CPULoadPercent),
			CPUTempC:        round1(info.CPUTempC),
			MemUsedPercent:  round1(info.MemUsedPercent),
			DiskUsedPercent: round1(info.DiskUsedPercent),
		}
		var buf bytes.Buffer
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			http.Error(w, `{"error":"encode response"}`, http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(buf.Bytes()) // the client is gone if this fails
	})
	return mux
}

func round1(v *float64) *float64 {
	if v == nil || math.IsNaN(*v) || math.IsInf(*v, 0) {
		return nil
	}
	r := math.Round(*v*10) / 10
	return &r
}

// ParseStat returns idle and total jiffies of the "cpu" line of /proc/stat.
func ParseStat(stat string) (idle, total uint64, ok bool) {
	sc := bufio.NewScanner(strings.NewReader(stat))
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) < 5 || f[0] != "cpu" {
			continue
		}
		for i, s := range f[1:] {
			v, err := strconv.ParseUint(s, 10, 64)
			if err != nil {
				return 0, 0, false
			}
			total += v
			if i == 3 || i == 4 { // idle, iowait
				idle += v
			}
		}
		return idle, total, true
	}
	return 0, 0, false
}

// ParseMeminfo returns the used memory in percent (1 - MemAvailable/MemTotal).
func ParseMeminfo(meminfo string) (float64, bool) {
	var total, avail float64
	sc := bufio.NewScanner(strings.NewReader(meminfo))
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) < 2 {
			continue
		}
		v, err := strconv.ParseFloat(f[1], 64)
		if err != nil {
			continue
		}
		switch f[0] {
		case "MemTotal:":
			total = v
		case "MemAvailable:":
			avail = v
		}
	}
	if total <= 0 {
		return 0, false
	}
	return 100 * (1 - avail/total), true
}

// PowerOff shuts the computer down like legacy CaSSAndRA (sudo shutdown -h
// now); the user running CaSSAndRA needs the right to do so.
func PowerOff(ctx context.Context) error {
	out, err := exec.CommandContext(ctx, "sudo", "-n", "shutdown", "-h", "now").CombinedOutput()
	if err != nil {
		return fmt.Errorf("shutdown: %w: %s", err, strings.TrimSpace(string(out)))
	}
	return nil
}
