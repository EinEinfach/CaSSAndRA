package server

import (
	"embed"
	"io/fs"
)

// dist is filled by the frontend build (web/ builds into server/dist).
//
//go:embed all:dist
var dist embed.FS

// EmbeddedUI returns the frontend compiled into the binary.
func EmbeddedUI() fs.FS {
	ui, err := fs.Sub(dist, "dist")
	if err != nil {
		// Unreachable: "dist" is a constant, valid path.
		panic(err)
	}
	return ui
}
