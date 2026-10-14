package protocol_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// golden returns a reply line from testdata exactly as the robot sends it.
func golden(t testing.TB, name string) string {
	t.Helper()
	b, err := os.ReadFile(filepath.Join("testdata", name+".txt"))
	if err != nil {
		t.Fatalf("read golden file: %v", err)
	}
	return string(b)
}

// payload unframes a golden reply line.
func payload(t *testing.T, name string) string {
	t.Helper()
	p, err := protocol.Unframe(golden(t, name))
	if err != nil {
		t.Fatalf("unframe %s: %v", name, err)
	}
	return p
}
