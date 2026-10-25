package mqttapi_test

import (
	"testing"
)

func TestScheduleTopicAndSave(t *testing.T) {
	f := newFixture(t)
	front := f.addTask(t, "Front")
	back := f.addTask(t, "Back")
	if got := string(topic(t, f.api.State(), "schedule")); got != `{"scheduleActive":false,"timeRange":[{"monday":[12.0,12.0]},{"tuesday":[12.0,12.0]},{"wednesday":[12.0,12.0]},{"thursday":[12.0,12.0]},{"friday":[12.0,12.0]},{"saturday":[12.0,12.0]},{"sunday":[12.0,12.0]}],"tasks":[{"monday":[]},{"tuesday":[]},{"wednesday":[]},{"thursday":[]},{"friday":[]},{"saturday":[]},{"sunday":[]}]}` {
		t.Errorf("schedule = %s", got)
	}
	handle(t, f.api, `{"schedule": {"command": "save", "value": {"scheduleActive": true,
		"timeRange": [{"monday": [9.5, 12]}, {"tuesday": [12, 12]}, {"wednesday": [7.25, 24]}, {"thursday": [12, 12]},
		              {"friday": [12, 12]}, {"saturday": [12, 12]}, {"sunday": [12, 12]}],
		"tasks": [{"monday": ["Back", "Front", "Gone"]}, {"tuesday": []}, {"wednesday": []}, {"thursday": []},
		          {"friday": []}, {"saturday": []}, {"sunday": []}]}}}`)
	s := f.schedule.Get()
	if !s.Active || s.Days[0].Start != "09:30" || s.Days[0].End != "12:00" || len(s.Days[0].TaskIDs) != 2 ||
		s.Days[0].TaskIDs[0] != back.ID || s.Days[0].TaskIDs[1] != front.ID || s.Days[2].Start != "07:15" || s.Days[2].End != "24:00" {
		t.Errorf("saved schedule = %+v", s)
	}
	got := string(topic(t, f.api.State(), "schedule"))
	if want := `{"scheduleActive":true,"timeRange":[{"monday":[9.5,12.0]},{"tuesday":[12.0,12.0]},{"wednesday":[7.25,24.0]},`; got[:len(want)] != want {
		t.Errorf("schedule = %s", got)
	}
}
