package mqttapi

import (
	"encoding/json"
	"fmt"
	"math"
	"strconv"
	"strings"

	"github.com/EinEinfach/CaSSAndRA/next/backend/schedule"
)

// Schedule is what the API needs from the schedule store.
type Schedule interface {
	Get() schedule.Schedule
	Set(s schedule.Schedule) error
}

// ScheduleJSON is the payload of <prefix>/schedule and the value of
// {"schedule": {"command": "save"}} (legacy ScheduleCfg.to_json): per
// weekday the window in hours ([9.5, 12.0]) and the task names.
type ScheduleJSON struct {
	ScheduleActive bool                  `json:"scheduleActive"`
	TimeRange      []map[string][]Float  `json:"timeRange"`
	Tasks          []map[string][]string `json:"tasks"`
}

func (a *API) scheduleJSON() ScheduleJSON {
	s := a.schedule.Get()
	out := ScheduleJSON{ScheduleActive: s.Active}
	for i, day := range schedule.Weekdays {
		d := s.Days[i]
		out.TimeRange = append(out.TimeRange, map[string][]Float{day: {hours(d.Start), hours(d.End)}})
		out.Tasks = append(out.Tasks, map[string][]string{day: a.taskNames(d.TaskIDs)})
	}
	return out
}

func hours(hhmm string) Float {
	h, m, _ := strings.Cut(hhmm, ":")
	hh, _ := strconv.Atoi(h)
	mm, _ := strconv.Atoi(m)
	return Float(float64(hh) + float64(mm)/60)
}

func clock(h float64) string {
	m := int(math.Round(math.Max(0, math.Min(24, h)) * 60))
	return fmt.Sprintf("%02d:%02d", m/60, m%60)
}

// scheduleCommand saves the schedule; task names are those of the active
// map, like legacy.
func (a *API) scheduleCommand(c command) error {
	if c.Command != "save" {
		return fmt.Errorf("%w: schedule command %q", ErrUnknown, c.Command)
	}
	var v struct {
		ScheduleActive bool                   `json:"scheduleActive"`
		TimeRange      []map[string][]float64 `json:"timeRange"`
		Tasks          []map[string][]string  `json:"tasks"`
	}
	if err := json.Unmarshal(c.Value, &v); err != nil {
		return fmt.Errorf("%w: schedule save: %w", ErrInvalid, err)
	}
	s := a.schedule.Get()
	s.Active = v.ScheduleActive
	for i, day := range schedule.Weekdays {
		for _, r := range v.TimeRange {
			if w, ok := r[day]; ok && len(w) == 2 {
				s.Days[i].Start, s.Days[i].End = clock(w[0]), clock(w[1])
			}
		}
		for _, t := range v.Tasks {
			if names, ok := t[day]; ok {
				s.Days[i].TaskIDs = a.taskIDs(names)
			}
		}
	}
	return a.schedule.Set(s)
}
