package maps_test

import (
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
)

func TestOpenStoreFresh(t *testing.T) {
	f := newStore(t)
	if !f.store.Fresh() {
		t.Error("Fresh = false for a new directory")
	}
	if _, err := os.Stat(f.dir); err != nil {
		t.Errorf("directory not created: %v", err)
	}
	if again := openStore(t, f.dir, f.clock); again.Fresh() {
		t.Error("Fresh = true for an existing directory")
	}
	if len(f.store.List()) != 0 || f.store.ActiveID() != "" {
		t.Error("new store is not empty")
	}
}

func TestCreateGetListAndReopen(t *testing.T) {
	f := newStore(t)
	b, err := f.store.Create(garden("beta"))
	if err != nil {
		t.Fatal(err)
	}
	f.clock.Advance(time.Minute)
	a, err := f.store.Create(garden("Alpha"))
	if err != nil {
		t.Fatal(err)
	}
	if b.ID != "m1" || a.ID != "m2" || !b.UpdatedAt.Equal(t0) || !a.UpdatedAt.Equal(t0.Add(time.Minute)) {
		t.Errorf("ids %q %q, times %v %v", b.ID, a.ID, b.UpdatedAt, a.UpdatedAt)
	}
	got, err := f.store.Get(b.ID)
	if err != nil || !reflect.DeepEqual(got, b) {
		t.Errorf("Get = %+v, %v", got, err)
	}
	names := func(list []maps.Map) []string {
		var n []string
		for _, m := range list {
			n = append(n, m.Name)
		}
		return n
	}
	if got := names(f.store.List()); !reflect.DeepEqual(got, []string{"Alpha", "beta"}) {
		t.Errorf("List = %v, want sorted by name ignoring case", got)
	}

	reopened := openStore(t, f.dir, f.clock)
	if !reflect.DeepEqual(reopened.List(), f.store.List()) {
		t.Error("maps differ after reopening")
	}
}

func TestCreateErrors(t *testing.T) {
	f := newStore(t)
	if _, err := f.store.Create(garden("Garden")); err != nil {
		t.Fatal(err)
	}
	if _, err := f.store.Create(garden("garden")); !errors.Is(err, maps.ErrNameTaken) {
		t.Errorf("duplicate name: err = %v, want ErrNameTaken", err)
	}
	bad := garden("Bad")
	bad.Perimeter = nil
	if _, err := f.store.Create(bad); !errors.Is(err, maps.ErrInvalid) {
		t.Errorf("invalid map: err = %v, want ErrInvalid", err)
	}
	if len(f.store.List()) != 1 {
		t.Error("failed creates stored a map")
	}
}

func TestUpdate(t *testing.T) {
	f := newStore(t)
	m, _ := f.store.Create(garden("Garden"))
	other, _ := f.store.Create(garden("Other"))
	f.clock.Advance(time.Hour)

	m.Name = "Renamed"
	m.Dock = nil
	updated, err := f.store.Update(m)
	if err != nil {
		t.Fatal(err)
	}
	if updated.Name != "Renamed" || len(updated.Dock) != 0 || !updated.UpdatedAt.Equal(t0.Add(time.Hour)) {
		t.Errorf("updated = %+v", updated)
	}
	m.Name = "Renamed" // same name as itself is fine
	if _, err := f.store.Update(m); err != nil {
		t.Errorf("keeping the name: %v", err)
	}
	other.Name = "renamed"
	if _, err := f.store.Update(other); !errors.Is(err, maps.ErrNameTaken) {
		t.Errorf("err = %v, want ErrNameTaken", err)
	}
	m.ID = "missing"
	if _, err := f.store.Update(m); !errors.Is(err, maps.ErrNotFound) {
		t.Errorf("err = %v, want ErrNotFound", err)
	}
}

func TestActive(t *testing.T) {
	f := newStore(t)
	m, _ := f.store.Create(garden("Garden"))
	if err := f.store.SetActive(m.ID); err != nil {
		t.Fatal(err)
	}
	if f.store.ActiveID() != m.ID {
		t.Errorf("active = %q", f.store.ActiveID())
	}
	if openStore(t, f.dir, f.clock).ActiveID() != m.ID {
		t.Error("active map not restored after reopening")
	}
	if err := f.store.SetActive("missing"); !errors.Is(err, maps.ErrNotFound) {
		t.Errorf("err = %v, want ErrNotFound", err)
	}
	if err := f.store.SetActive(""); err != nil || f.store.ActiveID() != "" {
		t.Errorf("deactivate: %v, active %q", err, f.store.ActiveID())
	}
}

func TestDelete(t *testing.T) {
	f := newStore(t)
	m, _ := f.store.Create(garden("Garden"))
	keep, _ := f.store.Create(garden("Keep"))
	_ = f.store.SetActive(m.ID)
	if err := f.store.Delete(m.ID); err != nil {
		t.Fatal(err)
	}
	if _, err := f.store.Get(m.ID); !errors.Is(err, maps.ErrNotFound) {
		t.Errorf("Get after delete: %v", err)
	}
	if f.store.ActiveID() != "" {
		t.Error("deleted map is still active")
	}
	if _, err := os.Stat(filepath.Join(f.dir, m.ID+".json")); !errors.Is(err, os.ErrNotExist) {
		t.Error("file not removed")
	}
	if err := f.store.Delete(m.ID); !errors.Is(err, maps.ErrNotFound) {
		t.Errorf("second delete: %v", err)
	}
	if list := openStore(t, f.dir, f.clock).List(); len(list) != 1 || list[0].ID != keep.ID {
		t.Errorf("after reopening: %+v", list)
	}
}

func TestOnChange(t *testing.T) {
	f := newStore(t)
	calls := 0
	f.store.OnChange(func() { calls++ })
	m, _ := f.store.Create(garden("Garden"))
	_, _ = f.store.Update(m)
	_ = f.store.SetActive(m.ID)
	_ = f.store.Delete(m.ID)
	_, _ = f.store.Create(maps.Map{}) // invalid: no change
	if calls != 4 {
		t.Errorf("calls = %d, want 4", calls)
	}
}

func TestOpenStoreErrors(t *testing.T) {
	tests := map[string]func(dir string){
		"broken map file": func(dir string) {
			_ = os.WriteFile(filepath.Join(dir, "x.json"), []byte("{"), 0o600)
		},
		"id does not match file name": func(dir string) {
			_ = os.WriteFile(filepath.Join(dir, "x.json"), []byte(`{"id": "y", "name": "n"}`), 0o600)
		},
		"broken active file": func(dir string) {
			_ = os.WriteFile(filepath.Join(dir, "active.json"), []byte("{"), 0o600)
		},
	}
	for name, prepare := range tests {
		t.Run(name, func(t *testing.T) {
			dir := t.TempDir()
			prepare(dir)
			if _, err := maps.OpenStore(dir, maps.StoreConfig{}); err == nil {
				t.Error("want an error")
			}
		})
	}
	t.Run("directory cannot be created", func(t *testing.T) {
		file := filepath.Join(t.TempDir(), "file")
		_ = os.WriteFile(file, nil, 0o600)
		if _, err := maps.OpenStore(filepath.Join(file, "maps"), maps.StoreConfig{}); err == nil {
			t.Error("want an error")
		}
	})
}

func TestActiveOfMissingMapIsIgnored(t *testing.T) {
	dir := t.TempDir()
	_ = os.WriteFile(filepath.Join(dir, "active.json"), []byte(`{"id": "gone"}`), 0o600)
	s, err := maps.OpenStore(dir, maps.StoreConfig{})
	if err != nil {
		t.Fatal(err)
	}
	if s.ActiveID() != "" {
		t.Errorf("active = %q, want none", s.ActiveID())
	}
}

func TestDefaultIDsAreUnique(t *testing.T) {
	s, err := maps.OpenStore(t.TempDir(), maps.StoreConfig{})
	if err != nil {
		t.Fatal(err)
	}
	a, _ := s.Create(garden("A"))
	b, _ := s.Create(garden("B"))
	if a.ID == "" || a.ID == b.ID || a.UpdatedAt.IsZero() {
		t.Errorf("ids %q %q, time %v", a.ID, b.ID, a.UpdatedAt)
	}
}

func TestWriteErrorsChangeNothing(t *testing.T) {
	if os.Geteuid() == 0 {
		t.Skip("root ignores file permissions")
	}
	f := newStore(t)
	m, _ := f.store.Create(garden("Garden"))
	if err := os.Chmod(f.dir, 0o500); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chmod(f.dir, 0o755) })

	if _, err := f.store.Create(garden("New")); err == nil {
		t.Error("Create in a read-only directory succeeded")
	}
	if err := f.store.SetActive(m.ID); err == nil || f.store.ActiveID() != "" {
		t.Errorf("SetActive: err %v, active %q", err, f.store.ActiveID())
	}
	if err := f.store.Delete(m.ID); err == nil {
		t.Error("Delete in a read-only directory succeeded")
	}
	if len(f.store.List()) != 1 {
		t.Error("map list changed")
	}
}

func TestDeleteActiveMapInReadOnlyDirectory(t *testing.T) {
	if os.Geteuid() == 0 {
		t.Skip("root ignores file permissions")
	}
	f := newStore(t)
	m, _ := f.store.Create(garden("Garden"))
	_ = f.store.SetActive(m.ID)
	_ = os.Chmod(f.dir, 0o500)
	t.Cleanup(func() { _ = os.Chmod(f.dir, 0o755) })
	if err := f.store.Delete(m.ID); err == nil || f.store.ActiveID() != m.ID {
		t.Errorf("err %v, active %q; want an error and nothing changed", err, f.store.ActiveID())
	}
}
