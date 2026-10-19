package tasks_test

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func task(name, mapID string) tasks.Task {
	return tasks.Task{Name: name, MapID: mapID, Parts: []tasks.Part{{Parameters: params}}}
}

func openStore(t *testing.T, path string) *tasks.Store {
	t.Helper()
	n := 0
	s, err := tasks.OpenStore(path, tasks.StoreConfig{
		NewID: func() string { n++; return "t" + string(rune('0'+n)) },
		Now:   testkit.NewFakeClock(t0).Now,
	})
	if err != nil {
		t.Fatal(err)
	}
	return s
}

func TestStoreKeepsTasks(t *testing.T) {
	path := filepath.Join(t.TempDir(), "tasks.json")
	s := openStore(t, path)
	changes := 0
	s.OnChange(func() { changes++ })

	front, err := s.Create(task("  Front  ", "m1"))
	if err != nil {
		t.Fatal(err)
	}
	if front.ID != "t1" || front.Name != "Front" || !front.UpdatedAt.Equal(t0) || front.Parts[0].Selection == nil {
		t.Errorf("created = %+v", front)
	}
	back, err := s.Create(task("Back", "m1"))
	if err != nil {
		t.Fatal(err)
	}
	front.Parts = append(front.Parts, tasks.Part{Selection: []geo.Point{{X: 1, Y: 1}, {X: 2, Y: 1}, {X: 2, Y: 2}}, Parameters: params})
	if _, err := s.Update(front); err != nil {
		t.Fatal(err)
	}
	if err := s.Delete(back.ID); err != nil {
		t.Fatal(err)
	}
	if changes != 4 {
		t.Errorf("%d change notifications, want 4", changes)
	}

	again := openStore(t, path)
	if !again.Exists() {
		t.Error("store does not exist after saving")
	}
	got, err := again.Get("t1")
	if err != nil || len(got.Parts) != 2 || len(again.List()) != 1 {
		t.Errorf("reopened: %+v, %v, %d tasks", got, err, len(again.List()))
	}
}

func TestStoreRefuses(t *testing.T) {
	s := openStore(t, filepath.Join(t.TempDir(), "tasks.json"))
	if _, err := s.Create(task("Front", "m1")); err != nil {
		t.Fatal(err)
	}
	tests := []struct {
		name string
		do   func() error
		want error
		msg  string
	}{
		{"same name on the same map", func() error { _, err := s.Create(task("FRONT", "m1")); return err }, tasks.ErrNameTaken, ""},
		{"no name", func() error { _, err := s.Create(task(" ", "m1")); return err }, tasks.ErrInvalid, "name"},
		{"no map", func() error { _, err := s.Create(task("X", "")); return err }, tasks.ErrInvalid, "mapId"},
		{"no parts", func() error {
			tk := task("X", "m1")
			tk.Parts = nil
			_, err := s.Create(tk)
			return err
		}, tasks.ErrInvalid, "parts"},
		{"invalid part", func() error {
			tk := task("X", "m1")
			tk.Parts[0].Parameters.WidthM = 0
			_, err := s.Create(tk)
			return err
		}, tasks.ErrInvalid, "part 1"},
		{"update of a missing task", func() error { tk := task("X", "m1"); tk.ID = "nope"; _, err := s.Update(tk); return err }, tasks.ErrNotFound, ""},
		{"delete of a missing task", func() error { return s.Delete("nope") }, tasks.ErrNotFound, ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.do()
			if !errors.Is(err, tt.want) || !strings.Contains(err.Error(), tt.msg) {
				t.Errorf("err = %v, want %v mentioning %q", err, tt.want, tt.msg)
			}
		})
	}
	if _, err := s.Create(task("Front", "m2")); err != nil {
		t.Errorf("the same name on another map: %v", err)
	}
}

func TestStoreDropsTasksOfDeletedMaps(t *testing.T) {
	s := openStore(t, filepath.Join(t.TempDir(), "tasks.json"))
	for _, tk := range []tasks.Task{task("A", "m1"), task("B", "m2"), task("C", "m2")} {
		if _, err := s.Create(tk); err != nil {
			t.Fatal(err)
		}
	}
	changes := 0
	s.OnChange(func() { changes++ })
	if err := s.KeepMaps(func(id string) bool { return id != "m2" }); err != nil {
		t.Fatal(err)
	}
	if err := s.KeepMaps(func(string) bool { return true }); err != nil {
		t.Fatal(err)
	}
	if list := s.List(); len(list) != 1 || list[0].Name != "A" || changes != 1 {
		t.Errorf("tasks %+v after %d changes, want only A after 1", list, changes)
	}
}

func TestBrokenTaskFileStopsTheStart(t *testing.T) {
	for name, content := range map[string]string{
		"not JSON":     `{`,
		"duplicate id": `{"tasks":[{"id":"a","name":"x"},{"id":"a","name":"y"}]}`,
		"missing id":   `{"tasks":[{"name":"x"}]}`,
	} {
		t.Run(name, func(t *testing.T) {
			path := filepath.Join(t.TempDir(), "tasks.json")
			if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
				t.Fatal(err)
			}
			if _, err := tasks.OpenStore(path, tasks.StoreConfig{}); err == nil {
				t.Error("broken file opened")
			}
		})
	}
}
