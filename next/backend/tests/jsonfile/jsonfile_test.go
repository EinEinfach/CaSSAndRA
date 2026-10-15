package jsonfile_test

import (
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/jsonfile"
)

type doc struct {
	Name  string `json:"name"`
	Count int    `json:"count"`
}

func TestWriteThenRead(t *testing.T) {
	path := filepath.Join(t.TempDir(), "sub", "doc.json") // directory is created
	if err := jsonfile.Write(path, doc{"a", 1}); err != nil {
		t.Fatal(err)
	}
	if err := jsonfile.Write(path, doc{"b", 2}); err != nil { // replaces
		t.Fatal(err)
	}
	var got doc
	if err := jsonfile.Read(path, &got); err != nil {
		t.Fatal(err)
	}
	if got != (doc{"b", 2}) {
		t.Errorf("got %+v", got)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if perm := info.Mode().Perm(); perm != 0o600 {
		t.Errorf("permissions = %o, want 600 (may hold passwords)", perm)
	}
	entries, _ := os.ReadDir(filepath.Dir(path))
	if len(entries) != 1 {
		t.Errorf("directory has %d entries, want only the file (no temp files left)", len(entries))
	}
}

func TestReadMissingFile(t *testing.T) {
	var d doc
	err := jsonfile.Read(filepath.Join(t.TempDir(), "missing.json"), &d)
	if !errors.Is(err, os.ErrNotExist) {
		t.Errorf("err = %v, want ErrNotExist", err)
	}
}

func TestReadInvalidJSON(t *testing.T) {
	path := filepath.Join(t.TempDir(), "bad.json")
	if err := os.WriteFile(path, []byte("{"), 0o600); err != nil {
		t.Fatal(err)
	}
	var d doc
	if err := jsonfile.Read(path, &d); err == nil {
		t.Error("want an error for invalid JSON")
	}
}

func TestWriteUnencodable(t *testing.T) {
	path := filepath.Join(t.TempDir(), "x.json")
	if err := jsonfile.Write(path, func() {}); err == nil {
		t.Error("want an error for a value JSON cannot encode")
	}
	if _, err := os.Stat(path); !errors.Is(err, os.ErrNotExist) {
		t.Error("nothing should be written")
	}
}

func TestWriteIntoMissingParentFails(t *testing.T) {
	file := filepath.Join(t.TempDir(), "file")
	if err := os.WriteFile(file, nil, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := jsonfile.Write(filepath.Join(file, "x.json"), doc{}); err == nil {
		t.Error("want an error when the parent is a file")
	}
}
