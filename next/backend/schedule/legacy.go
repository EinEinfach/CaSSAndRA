package schedule

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"slices"
)

// legacyFile is user/schedulecfg.json of the legacy app: per weekday a
// window in hours ([9.5, 12] = 09:30 to 12:00) and the names of the tasks.
type legacyFile struct {
	UseSchedule bool                   `json:"use_schedule"`
	TimeRange   []map[string][]float64 `json:"time_range"`
	Tasks       []map[string][]string  `json:"tasks"`
}

// LegacyImport is the result of ImportLegacy.
type LegacyImport struct {
	Schedule Schedule
	Warnings []string
}

// ImportLegacy reads the legacy schedule from path. taskID finds the ID of
// a task by its legacy name (the legacy schedule names tasks of the map that
// was active); unknown names are dropped with a warning.
func ImportLegacy(path string, taskID func(name string) (string, bool)) (LegacyImport, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return LegacyImport{}, fmt.Errorf("import legacy schedule: %w", err)
	}
	var f legacyFile
	if err := json.Unmarshal(data, &f); err != nil {
		return LegacyImport{}, fmt.Errorf("import legacy schedule: %w", err)
	}
	out := LegacyImport{Schedule: Default()}
	out.Schedule.Active = f.UseSchedule
	for i, name := range Weekdays {
		d := &out.Schedule.Days[i]
		for _, r := range f.TimeRange {
			if w, ok := r[name]; ok && len(w) == 2 {
				d.Start, d.End = hours(w[0]), hours(w[1])
			}
		}
		if _, _, ok := d.window(); !ok {
			d.Start, d.End = "12:00", "12:00"
		}
		for _, t := range f.Tasks {
			for _, n := range t[name] {
				id, ok := taskID(n)
				switch {
				case !ok:
					out.Warnings = append(out.Warnings, fmt.Sprintf("%s: task %q not found, dropped", name, n))
				case len(d.TaskIDs) < maxTasksPerDay && !slices.Contains(d.TaskIDs, id):
					d.TaskIDs = append(d.TaskIDs, id)
				}
			}
		}
	}
	if err := out.Schedule.Validate(); err != nil {
		return LegacyImport{}, fmt.Errorf("import legacy schedule: %w", err)
	}
	return out, nil
}

// hours turns legacy hours (9.5) into "09:30", within 00:00 and 24:00.
func hours(h float64) string {
	m := int(math.Round(math.Max(0, math.Min(24, h)) * 60))
	return clock(m)
}
