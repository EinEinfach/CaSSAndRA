package maps_test

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
)

// testdata/legacy/perimeter.json is a pandas DataFrame as legacy CaSSAndRA
// saves it (to_json, orient "columns"): closed polygons, exclusions numbered
// out of order, rows of one map not contiguous and a broken map.
func TestImportLegacy(t *testing.T) {
	got, err := maps.ImportLegacy("testdata/legacy")
	if err != nil {
		t.Fatal(err)
	}
	want := []maps.Map{
		{
			Name:      "Garden",
			Perimeter: pts(0, 0, 10, 0, 10, 10, 0, 10),
			// exclusion_2 before exclusion_10: numeric, not text order
			Exclusions: [][]geo.Point{pts(6, 6, 7, 6, 7, 7, 6, 7), pts(2, 2, 3, 2, 3, 3)},
			Dock:       pts(1, 1, 1, 2, -1, 2),
			SearchWire: pts(0.5, 0.5, 5, 0.5),
		},
		{
			Name:       "Yard",
			Perimeter:  pts(0, 0, 20, 0, 20, 5, 0, 5),
			Exclusions: [][]geo.Point{},
			Dock:       pts(5, 5, 6, 5),
			SearchWire: []geo.Point{},
		},
	}
	if !reflect.DeepEqual(got.Maps, want) {
		t.Errorf("maps\n got %+v\nwant %+v", got.Maps, want)
	}
	if got.Active != "Yard" {
		t.Errorf("active = %q, want Yard (tmp.json)", got.Active)
	}
	if len(got.Warnings) != 1 || !strings.Contains(got.Warnings[0], `"Broken"`) {
		t.Errorf("warnings = %q, want one about the broken map", got.Warnings)
	}
}

func TestImportLegacyWithoutFiles(t *testing.T) {
	got, err := maps.ImportLegacy(t.TempDir())
	if err != nil || len(got.Maps) != 0 || got.Active != "" || len(got.Warnings) != 0 {
		t.Errorf("got %+v, %v; want empty", got, err)
	}
}

func TestImportLegacyProblems(t *testing.T) {
	frame := func(x, typ string) string {
		return `{"X": {"0": ` + x + `, "1": 1, "2": 1}, "Y": {"0": 0, "1": 0, "2": 1},
			"type": {"0": "` + typ + `", "1": "perimeter", "2": "perimeter"},
			"name": {"0": "M", "1": "M", "2": "M"}}`
	}
	tests := []struct {
		name, perimeter, tmp string
		wantErr              bool
		wantWarning          string
		wantActive           string
	}{
		{"missing coordinate", frame("null", "perimeter"), "", false, "no coordinates", ""},
		{"unknown type", frame("0", "garage"), "", false, `unknown type "garage"`, ""},
		{"bad exclusion number", frame("0", "exclusion_x"), "", false, `unknown type "exclusion_x"`, ""},
		{"active map", frame("0", "perimeter"), `{"PERIMETERNAME": "M"}`, false, "", "M"},
		{"active map missing", frame("0", "perimeter"), `{"PERIMETERNAME": "Other"}`, false, "", ""},
		{"broken tmp.json", frame("0", "perimeter"), `{`, false, "active map", ""},
		{"not json", `{`, "", true, "", ""},
		{"row is not a number", `{"X": {"a": 1}, "Y": {"a": 1}, "type": {"a": "perimeter"}, "name": {"a": "M"}}`, "", true, "", ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dir := t.TempDir()
			_ = os.WriteFile(filepath.Join(dir, "perimeter.json"), []byte(tt.perimeter), 0o600)
			if tt.tmp != "" {
				_ = os.WriteFile(filepath.Join(dir, "tmp.json"), []byte(tt.tmp), 0o600)
			}
			got, err := maps.ImportLegacy(dir)
			if (err != nil) != tt.wantErr {
				t.Fatalf("err = %v, want error %v", err, tt.wantErr)
			}
			if tt.wantErr {
				return
			}
			warned := strings.Join(got.Warnings, "\n")
			if (tt.wantWarning == "") != (warned == "") || !strings.Contains(warned, tt.wantWarning) {
				t.Errorf("warnings = %q, want %q", got.Warnings, tt.wantWarning)
			}
			if got.Active != tt.wantActive {
				t.Errorf("active = %q, want %q", got.Active, tt.wantActive)
			}
		})
	}
}

func TestStoreImport(t *testing.T) {
	f := newStore(t)
	if _, err := f.store.Create(garden("Garden")); err != nil { // taken name
		t.Fatal(err)
	}
	li, err := maps.ImportLegacy("testdata/legacy")
	if err != nil {
		t.Fatal(err)
	}
	n, warnings := f.store.Import(li)
	if n != 1 {
		t.Errorf("imported %d, want 1 (Yard)", n)
	}
	// broken map from the file + taken name
	if len(warnings) != 2 || !strings.Contains(warnings[1], "Garden") {
		t.Errorf("warnings = %q", warnings)
	}
	active, err := f.store.Get(f.store.ActiveID())
	if err != nil || active.Name != "Yard" {
		t.Errorf("active = %+v, %v; want Yard", active, err)
	}
}
