// Package architecture_test enforces the structure rules from CLAUDE.md:
// flat feature folders, tests mirrored under tests/, and dependencies that
// only point downwards.
package architecture_test

import (
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"testing"
)

const module = "github.com/EinEinfach/CaSSAndRA/next/backend"

// testOnlyDirs live under tests/ without a matching feature.
var testOnlyDirs = []string{"architecture", "integration", "testkit"}

// allowedDeps restricts the low-level features. Features not listed here may
// import any feature except the ones in topLevel.
var allowedDeps = map[string][]string{
	"geo":      {},
	"protocol": {"geo"},
	"link":     {"geo", "protocol"},
}

// topLevel features may only be imported by app (and main).
var topLevel = []string{"app", "server", "mqttapi"}

func root(t *testing.T) string {
	t.Helper()
	dir, err := filepath.Abs(filepath.Join("..", ".."))
	if err != nil {
		t.Fatal(err)
	}
	return dir
}

func subdirs(t *testing.T, dir string) []string {
	t.Helper()
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatal(err)
	}
	var names []string
	for _, e := range entries {
		if e.IsDir() && !strings.HasPrefix(e.Name(), ".") {
			names = append(names, e.Name())
		}
	}
	return names
}

func goFiles(t *testing.T, dir string) []string {
	t.Helper()
	matches, err := filepath.Glob(filepath.Join(dir, "*.go"))
	if err != nil {
		t.Fatal(err)
	}
	return matches
}

func features(t *testing.T) []string {
	t.Helper()
	var names []string
	for _, name := range subdirs(t, root(t)) {
		if name != "tests" && len(goFiles(t, filepath.Join(root(t), name))) > 0 {
			names = append(names, name)
		}
	}
	if len(names) == 0 {
		t.Fatal("no features found; is the test running from backend/tests/architecture?")
	}
	return names
}

func TestEveryFeatureHasMirroredTests(t *testing.T) {
	for _, f := range features(t) {
		if _, err := os.Stat(filepath.Join(root(t), "tests", f)); err != nil {
			t.Errorf("feature %q has no tests/%s folder", f, f)
		}
	}
}

func TestEveryTestFolderMirrorsAFeature(t *testing.T) {
	feats := features(t)
	for _, dir := range subdirs(t, filepath.Join(root(t), "tests")) {
		if !slices.Contains(feats, dir) && !slices.Contains(testOnlyDirs, dir) {
			t.Errorf("tests/%s has no matching feature folder", dir)
		}
	}
}

func TestFeaturesAreFlat(t *testing.T) {
	for _, f := range features(t) {
		dir := filepath.Join(root(t), f)
		err := filepath.WalkDir(dir, func(path string, d os.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if !d.IsDir() && filepath.Ext(path) == ".go" && filepath.Dir(path) != dir {
				t.Errorf("%s: features must not have Go code in subfolders", rel(t, path))
			}
			return nil
		})
		if err != nil {
			t.Fatal(err)
		}
	}
}

func TestNoTestsInsideFeatures(t *testing.T) {
	for _, f := range features(t) {
		for _, file := range goFiles(t, filepath.Join(root(t), f)) {
			if strings.HasSuffix(file, "_test.go") {
				t.Errorf("%s: tests belong in tests/%s", rel(t, file), f)
			}
		}
	}
}

func TestTestFoldersOnlyContainTests(t *testing.T) {
	for _, dir := range subdirs(t, filepath.Join(root(t), "tests")) {
		if dir == "testkit" {
			continue
		}
		for _, file := range goFiles(t, filepath.Join(root(t), "tests", dir)) {
			if !strings.HasSuffix(file, "_test.go") {
				t.Errorf("%s: only _test.go files belong here; shared helpers go to tests/testkit", rel(t, file))
			}
		}
	}
}

func TestDependencyDirection(t *testing.T) {
	for _, f := range features(t) {
		for _, file := range goFiles(t, filepath.Join(root(t), f)) {
			for _, imp := range moduleImports(t, file) {
				if msg := checkImport(f, imp); msg != "" {
					t.Errorf("%s imports %q: %s", rel(t, file), imp, msg)
				}
			}
		}
	}
}

func TestCheckImportRules(t *testing.T) {
	tests := []struct {
		from, to string
		allowed  bool
	}{
		{"geo", "protocol", false},
		{"protocol", "geo", true},
		{"protocol", "robot", false},
		{"link", "protocol", true},
		{"link", "robot", false},
		{"robot", "link", true},
		{"tasks", "maps", true},
		{"robot", "server", false},
		{"server", "mqttapi", false},
		{"app", "server", true},
		{"server", "app", false},
		{"robot", "tests/testkit", false},
	}
	for _, tt := range tests {
		if got := checkImport(tt.from, tt.to) == ""; got != tt.allowed {
			t.Errorf("%s -> %s allowed = %v, want %v", tt.from, tt.to, got, tt.allowed)
		}
	}
}

// checkImport returns why feature from may not import the module path to,
// or "" if the import is fine.
func checkImport(from, to string) string {
	if strings.HasPrefix(to, "tests/") {
		return "feature code must not import test helpers"
	}
	target := strings.SplitN(to, "/", 2)[0]
	if allowed, ok := allowedDeps[from]; ok && !slices.Contains(allowed, target) {
		if len(allowed) == 0 {
			return from + " must not import other features"
		}
		return from + " may only import " + strings.Join(allowed, ", ")
	}
	if slices.Contains(topLevel, target) && from != "app" {
		return target + " is top level and may only be imported by app"
	}
	return ""
}

// moduleImports returns the imports of file that belong to this module,
// relative to the module root.
func moduleImports(t *testing.T, file string) []string {
	t.Helper()
	f, err := parser.ParseFile(token.NewFileSet(), file, nil, parser.ImportsOnly)
	if err != nil {
		t.Fatal(err)
	}
	var imports []string
	for _, spec := range f.Imports {
		path, err := strconv.Unquote(spec.Path.Value)
		if err != nil {
			t.Fatal(err)
		}
		if rest, ok := strings.CutPrefix(path, module+"/"); ok {
			imports = append(imports, rest)
		}
	}
	return imports
}

func rel(t *testing.T, path string) string {
	t.Helper()
	r, err := filepath.Rel(root(t), path)
	if err != nil {
		return path
	}
	return r
}
