package schedule_test

import (
	"path/filepath"
	"slices"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/schedule"
)

func TestImportLegacy(t *testing.T) {
	ids := map[string]string{"front lawn": "t1", "back lawn": "t2"}
	got, err := schedule.ImportLegacy(filepath.Join("testdata", "schedulecfg.json"), func(name string) (string, bool) {
		id, ok := ids[name]
		return id, ok
	})
	if err != nil {
		t.Fatal(err)
	}
	s := got.Schedule
	if !s.Active {
		t.Error("use_schedule was true")
	}
	want := []schedule.Day{
		{Start: "09:30", End: "12:00", TaskIDs: []string{"t1", "t2"}},
		{Start: "12:00", End: "12:00", TaskIDs: []string{}},
		{Start: "07:15", End: "20:30", TaskIDs: []string{"t1"}},
		{Start: "12:00", End: "12:00", TaskIDs: []string{}},
		{Start: "00:00", End: "24:00", TaskIDs: []string{}},
	}
	for i, w := range want {
		d := s.Days[i]
		if d.Start != w.Start || d.End != w.End || !slices.Equal(d.TaskIDs, w.TaskIDs) {
			t.Errorf("%s = %+v, want %+v", schedule.Weekdays[i], d, w)
		}
	}
	if len(got.Warnings) != 1 {
		t.Errorf("warnings = %q, want one for the unknown task", got.Warnings)
	}
}

func TestImportLegacyFailsOnBrokenFiles(t *testing.T) {
	if _, err := schedule.ImportLegacy(filepath.Join("testdata", "missing.json"), nil); err == nil {
		t.Error("imported a missing file")
	}
}
