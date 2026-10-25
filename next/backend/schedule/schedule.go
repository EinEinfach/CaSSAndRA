// Package schedule starts and stops mowing according to a weekly plan: one
// time window per weekday with the tasks to mow in it.
package schedule

import (
	"errors"
	"fmt"
	"slices"
	"strconv"
	"strings"
	"time"
)

// ErrInvalid means a schedule was rejected; the returned errors wrap it.
var ErrInvalid = errors.New("invalid schedule")

// Weekdays names the days of Schedule.Days, Monday first.
var Weekdays = [7]string{"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}

const maxTasksPerDay = 20

// Day is the time window of one weekday, in local time ("HH:MM"). A window
// that ends where it starts is a day off. Tasks are mowed in this order; no
// tasks means the robot continues the route it has.
type Day struct {
	Start   string   `json:"start"`
	End     string   `json:"end"`
	TaskIDs []string `json:"taskIds"`
}

// Schedule is the weekly plan. Days are Monday first.
type Schedule struct {
	Active bool   `json:"active"`
	Days   [7]Day `json:"days"`
}

// Default is an inactive schedule with every day off.
func Default() Schedule {
	var s Schedule
	for i := range s.Days {
		s.Days[i] = Day{Start: "12:00", End: "12:00", TaskIDs: []string{}}
	}
	return s
}

// Validate checks the times and the task lists.
func (s Schedule) Validate() error {
	for i, d := range s.Days {
		start, err := minutes(d.Start)
		if err != nil {
			return fmt.Errorf("%w: %s start: %w", ErrInvalid, Weekdays[i], err)
		}
		end, err := minutes(d.End)
		if err != nil {
			return fmt.Errorf("%w: %s end: %w", ErrInvalid, Weekdays[i], err)
		}
		if end < start {
			return fmt.Errorf("%w: %s ends before it starts", ErrInvalid, Weekdays[i])
		}
		if len(d.TaskIDs) > maxTasksPerDay {
			return fmt.Errorf("%w: %s has more than %d tasks", ErrInvalid, Weekdays[i], maxTasksPerDay)
		}
		for j, id := range d.TaskIDs {
			if id == "" || slices.Contains(d.TaskIDs[:j], id) {
				return fmt.Errorf("%w: %s has an empty or repeated task", ErrInvalid, Weekdays[i])
			}
		}
	}
	return nil
}

func (s Schedule) normalized() Schedule {
	for i := range s.Days {
		if s.Days[i].TaskIDs == nil {
			s.Days[i].TaskIDs = []string{}
		}
	}
	return s
}

// window returns the minutes after midnight the day starts and ends; ok is
// false on a day off.
func (d Day) window() (start, end int, ok bool) {
	start, err1 := minutes(d.Start)
	end, err2 := minutes(d.End)
	return start, end, err1 == nil && err2 == nil && end > start
}

// minutes parses "HH:MM" (00:00 to 24:00).
func minutes(hhmm string) (int, error) {
	h, m, ok := strings.Cut(hhmm, ":")
	hours, err1 := strconv.Atoi(h)
	mins, err2 := strconv.Atoi(m)
	if !ok || len(h) != 2 || len(m) != 2 || err1 != nil || err2 != nil ||
		hours < 0 || mins < 0 || mins > 59 || hours*60+mins > 24*60 {
		return 0, fmt.Errorf("%q is not a time from 00:00 to 24:00", hhmm)
	}
	return hours*60 + mins, nil
}

// clock formats minutes after midnight as "HH:MM".
func clock(min int) string {
	return fmt.Sprintf("%02d:%02d", min/60, min%60)
}

// dayIndex is the index in Schedule.Days of t's weekday.
func dayIndex(t time.Time) int {
	return (int(t.Weekday()) + 6) % 7
}

// minuteOfDay is the number of whole minutes since midnight at t.
func minuteOfDay(t time.Time) int {
	return t.Hour()*60 + t.Minute()
}
