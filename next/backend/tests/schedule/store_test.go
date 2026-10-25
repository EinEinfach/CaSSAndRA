package schedule_test

import (
	"errors"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/schedule"
)

func TestANewStoreHasAnInactiveScheduleWithDaysOff(t *testing.T) {
	s, err := schedule.OpenStore(filepath.Join(t.TempDir(), "schedule.json"))
	if err != nil {
		t.Fatal(err)
	}
	got := s.Get()
	if s.Exists() || got.Active {
		t.Errorf("exists %v, active %v; want neither", s.Exists(), got.Active)
	}
	for i, d := range got.Days {
		if d.Start != d.End || d.TaskIDs == nil {
			t.Errorf("day %d = %+v, want a day off with an empty task list", i, d)
		}
	}
}

func TestTheStoreKeepsTheSchedule(t *testing.T) {
	path := filepath.Join(t.TempDir(), "schedule.json")
	s, _ := schedule.OpenStore(path)
	want := schedule.Default()
	want.Active = true
	want.Days[2] = schedule.Day{Start: "07:30", End: "24:00", TaskIDs: []string{"a", "b"}}
	changes := 0
	s.OnChange(func() { changes++ })
	if err := s.Set(want); err != nil {
		t.Fatal(err)
	}
	if changes != 1 {
		t.Errorf("changes = %d, want 1", changes)
	}
	reopened, err := schedule.OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	got := reopened.Get()
	if !reopened.Exists() || !got.Active || !slices.Equal(got.Days[2].TaskIDs, []string{"a", "b"}) || got.Days[2].End != "24:00" {
		t.Errorf("reopened = %+v", got)
	}
	got.Days[2].TaskIDs[0] = "changed"
	if s.Get().Days[2].TaskIDs[0] != "a" {
		t.Error("Get returns the stored slices; callers can change the store")
	}
}

func TestTheStoreRejects(t *testing.T) {
	tests := []struct {
		name string
		day  schedule.Day
		want string
	}{
		{"a missing time", schedule.Day{Start: "", End: "12:00"}, "monday start"},
		{"hours without leading zero", schedule.Day{Start: "9:00", End: "12:00"}, "monday start"},
		{"minutes over 59", schedule.Day{Start: "09:60", End: "12:00"}, "monday start"},
		{"after midnight", schedule.Day{Start: "09:00", End: "24:01"}, "monday end"},
		{"an end before the start", schedule.Day{Start: "12:00", End: "09:00"}, "ends before it starts"},
		{"a task twice", schedule.Day{Start: "09:00", End: "12:00", TaskIDs: []string{"a", "a"}}, "repeated"},
		{"an empty task", schedule.Day{Start: "09:00", End: "12:00", TaskIDs: []string{""}}, "empty"},
		{"too many tasks", schedule.Day{Start: "09:00", End: "12:00", TaskIDs: strings.Split("a b c d e f g h i j k l m n o p q r s t u", " ")}, "more than 20"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s, _ := schedule.OpenStore(filepath.Join(t.TempDir(), "schedule.json"))
			sched := schedule.Default()
			sched.Days[0] = tt.day
			err := s.Set(sched)
			if !errors.Is(err, schedule.ErrInvalid) || !strings.Contains(err.Error(), tt.want) {
				t.Errorf("err = %v, want ErrInvalid mentioning %q", err, tt.want)
			}
		})
	}
}

func TestABrokenFileStopsTheStart(t *testing.T) {
	for name, content := range map[string]string{
		"not JSON":     "{",
		"invalid time": `{"active":true,"days":[{"start":"25:00","end":"26:00","taskIds":[]}]}`,
	} {
		t.Run(name, func(t *testing.T) {
			path := filepath.Join(t.TempDir(), "schedule.json")
			if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
				t.Fatal(err)
			}
			if _, err := schedule.OpenStore(path); err == nil {
				t.Error("opened a broken file")
			}
		})
	}
}

func TestKeepTasksDropsDeletedTasks(t *testing.T) {
	s, _ := schedule.OpenStore(filepath.Join(t.TempDir(), "schedule.json"))
	sched := schedule.Default()
	sched.Days[0].TaskIDs = []string{"a", "gone", "b"}
	sched.Days[3].TaskIDs = []string{"gone"}
	if err := s.Set(sched); err != nil {
		t.Fatal(err)
	}
	changes := 0
	s.OnChange(func() { changes++ })
	keep := func(id string) bool { return id != "gone" }
	if err := s.KeepTasks(keep); err != nil {
		t.Fatal(err)
	}
	got := s.Get()
	if !slices.Equal(got.Days[0].TaskIDs, []string{"a", "b"}) || len(got.Days[3].TaskIDs) != 0 || got.Days[3].TaskIDs == nil {
		t.Errorf("days = %+v", got.Days)
	}
	if err := s.KeepTasks(keep); err != nil || changes != 1 {
		t.Errorf("changes = %d (err %v), want 1: nothing to drop the second time", changes, err)
	}
}
