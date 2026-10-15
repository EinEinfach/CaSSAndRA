package settings_test

import (
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
)

func TestOpenWithoutFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "settings.json")
	s, err := settings.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	if s.Exists() {
		t.Error("Exists = true before the first Set")
	}
	if s.Get() != settings.Default() {
		t.Errorf("got %+v, want defaults", s.Get())
	}
	if _, err := os.Stat(path); !errors.Is(err, os.ErrNotExist) {
		t.Error("Open must not write a file")
	}
}

func TestSetSavesAndReopens(t *testing.T) {
	path := filepath.Join(t.TempDir(), "settings.json")
	s, _ := settings.Open(path)
	next := settings.Default()
	next.Rover.MowSpeedMps = 0.42
	if err := s.Set(next); err != nil {
		t.Fatal(err)
	}
	if !s.Exists() {
		t.Error("Exists = false after Set")
	}
	again, err := settings.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	if again.Get() != next {
		t.Errorf("reopened %+v, want %+v", again.Get(), next)
	}
}

func TestSetRejectsInvalid(t *testing.T) {
	path := filepath.Join(t.TempDir(), "settings.json")
	s, _ := settings.Open(path)
	called := false
	s.OnChange(func(_, _ settings.Settings) { called = true })
	bad := settings.Default()
	bad.Planner.Pattern = "spiral"
	if err := s.Set(bad); !errors.Is(err, settings.ErrInvalid) {
		t.Errorf("err = %v, want ErrInvalid", err)
	}
	if called || s.Exists() || s.Get() != settings.Default() {
		t.Error("an invalid Set must change nothing")
	}
}

func TestSetWriteError(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "data")
	s, err := settings.Open(filepath.Join(dir, "settings.json"))
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(dir, nil, 0o600); err != nil { // the directory cannot be created any more
		t.Fatal(err)
	}
	next := settings.Default()
	next.Rover.MowSpeedMps = 0.42
	if err := s.Set(next); err == nil || errors.Is(err, settings.ErrInvalid) {
		t.Errorf("err = %v, want a write error", err)
	}
	if s.Get() != settings.Default() {
		t.Error("settings changed although saving failed")
	}
}

func TestOnChange(t *testing.T) {
	s, _ := settings.Open(filepath.Join(t.TempDir(), "settings.json"))
	var calls [][2]float64
	s.OnChange(func(old, next settings.Settings) {
		calls = append(calls, [2]float64{old.Rover.MowSpeedMps, next.Rover.MowSpeedMps})
	})
	next := settings.Default()
	for _, v := range []float64{0.3, 0.5} {
		next.Rover.MowSpeedMps = v
		if err := s.Set(next); err != nil {
			t.Fatal(err)
		}
	}
	want := [][2]float64{{0.25, 0.3}, {0.3, 0.5}}
	if len(calls) != 2 || calls[0] != want[0] || calls[1] != want[1] {
		t.Errorf("calls = %v, want %v", calls, want)
	}
}

func TestOpenFillsMissingFieldsWithDefaults(t *testing.T) {
	path := filepath.Join(t.TempDir(), "settings.json")
	if err := os.WriteFile(path, []byte(`{"rover": {"mowSpeedMps": 0.33}}`), 0o600); err != nil {
		t.Fatal(err)
	}
	s, err := settings.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	want := settings.Default()
	want.Rover = settings.Rover{MowSpeedMps: 0.33}
	want.Rover.GotoSpeedMps = settings.Default().Rover.GotoSpeedMps
	want.Rover.FixTimeoutSec = settings.Default().Rover.FixTimeoutSec
	if got := s.Get(); got != want {
		t.Errorf("got %+v\nwant %+v", got, want)
	}
}

func TestOpenBrokenFile(t *testing.T) {
	for name, content := range map[string]string{
		"not json": "{",
		"invalid":  `{"planner": {"pattern": "spiral"}}`,
	} {
		t.Run(name, func(t *testing.T) {
			path := filepath.Join(t.TempDir(), "settings.json")
			if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
				t.Fatal(err)
			}
			if _, err := settings.Open(path); err == nil {
				t.Error("want an error, not silently replaced settings")
			}
		})
	}
}
