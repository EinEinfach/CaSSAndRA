package tasks_test

import (
	"path/filepath"
	"slices"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tasks"
)

func TestImportLegacyTasks(t *testing.T) {
	li, err := tasks.ImportLegacy("testdata/legacy", map[string]string{"Garden": "g1", "Yard": "y1"})
	if err != nil {
		t.Fatal(err)
	}
	if len(li.Tasks) != 2 {
		t.Fatalf("tasks = %+v, want Front lawn and Everything", li.Tasks)
	}
	front, all := li.Tasks[0], li.Tasks[1]

	if front.Name != "Front lawn" || front.MapID != "g1" || len(front.Parts) != 2 {
		t.Fatalf("front = %+v", front)
	}
	lasso := []geo.Point{{X: 1, Y: 1}, {X: 4, Y: 1}, {X: 4, Y: 4}, {X: 1, Y: 4}}
	if !slices.Equal(front.Parts[0].Selection, lasso) {
		t.Errorf("part 1 selection = %v, want the lasso", front.Parts[0].Selection)
	}
	want := tasks.Parameters{Pattern: "lines", WidthM: 0.2, AngleDeg: 105, DistanceToBorder: 1,
		MowArea: true, BorderLaps: 2, MowExclusions: true}
	if front.Parts[0].Parameters != want {
		t.Errorf("part 1 parameters = %+v, want %+v", front.Parts[0].Parameters, want)
	}
	rect := []geo.Point{{X: 5, Y: 6}, {X: 8, Y: 6}, {X: 8, Y: 9}, {X: 5, Y: 9}}
	if !slices.Equal(front.Parts[1].Selection, rect) {
		t.Errorf("part 2 selection = %v, want the range as rectangle", front.Parts[1].Selection)
	}
	if p := front.Parts[1].Parameters; p.Pattern != "rings" || p.AngleDeg != 0 || !p.BorderCCW {
		t.Errorf("part 2 parameters = %+v, want rings, no angle (legacy: random) as 0, ccw", p)
	}

	if all.Name != "Everything" || all.MapID != "y1" || len(all.Parts) != 1 {
		t.Fatalf("everything = %+v", all)
	}
	if p := all.Parts[0]; len(p.Selection) != 0 || p.Selection == nil || p.Parameters.AngleDeg != 40 {
		t.Errorf("everything part = %+v, want the whole map (empty selection) and angle 400° as 40°", p)
	}

	warnings := strings.Join(li.Warnings, "\n")
	for _, w := range []string{`"Lost" skipped: map "Gone"`, `"Bad" skipped`} {
		if !strings.Contains(warnings, w) {
			t.Errorf("warnings %q do not mention %s", warnings, w)
		}
	}
}

func TestImportLegacyWithoutTasks(t *testing.T) {
	li, err := tasks.ImportLegacy(t.TempDir(), nil)
	if err != nil || len(li.Tasks) != 0 || len(li.Warnings) != 0 {
		t.Errorf("import = %+v, %v; want nothing", li, err)
	}
}

func TestImportStoresTasksOnce(t *testing.T) {
	path := filepath.Join(t.TempDir(), "tasks.json")
	store, err := tasks.OpenStore(path, tasks.StoreConfig{})
	if err != nil {
		t.Fatal(err)
	}
	if store.Exists() {
		t.Fatal("a new store exists")
	}
	li, err := tasks.ImportLegacy("testdata/legacy", map[string]string{"Garden": "g1", "Yard": "y1"})
	if err != nil {
		t.Fatal(err)
	}
	li.Tasks = append(li.Tasks, li.Tasks[0]) // the same name twice
	n, warnings := store.Import(li)
	if n != 2 || len(warnings) != 3 {
		t.Errorf("imported %d, warnings %q", n, warnings)
	}

	empty, err := tasks.OpenStore(filepath.Join(t.TempDir(), "tasks.json"), tasks.StoreConfig{})
	if err != nil {
		t.Fatal(err)
	}
	empty.Import(tasks.LegacyImport{})
	if !empty.Exists() {
		t.Error("after an import without tasks the file is missing; the next start would import again")
	}
}
