//go:build cpp

package planner

/*
#cgo CXXFLAGS: -std=c++20 -I${SRCDIR}/../../third_party/PathPlannerCore/include
#cgo CFLAGS: -I${SRCDIR}/../../third_party/PathPlannerCore/include
#include <stdlib.h>
#include "planner_c.h"
*/
import "C"

import (
	"fmt"
	"math"
	"unsafe"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
)

const available = true

func version() string { return C.GoString(C.planner_version()) }

// cArena holds C memory for one call. cgo forbids passing Go memory that
// contains Go pointers, and the environment is all pointers.
type cArena struct{ ptrs []unsafe.Pointer }

func (a *cArena) alloc(size uintptr) unsafe.Pointer {
	if size == 0 {
		return nil
	}
	p := C.calloc(1, C.size_t(size))
	if p == nil {
		panic("planner: out of memory")
	}
	a.ptrs = append(a.ptrs, p)
	return p
}

func (a *cArena) free() {
	for _, p := range a.ptrs {
		C.free(p)
	}
}

func (a *cArena) line(pts []geo.Point) C.planner_line {
	buf := unsafe.Slice((*C.planner_point)(a.alloc(uintptr(len(pts))*C.sizeof_planner_point)), len(pts))
	for i, p := range pts {
		buf[i] = C.planner_point{x: C.double(p.X), y: C.double(p.Y)}
	}
	return C.planner_line{points: unsafe.SliceData(buf), count: C.size_t(len(pts))}
}

func (a *cArena) lines(polys [][]geo.Point) (*C.planner_line, C.size_t) {
	buf := unsafe.Slice((*C.planner_line)(a.alloc(uintptr(len(polys))*C.sizeof_planner_line)), len(polys))
	for i, p := range polys {
		buf[i] = a.line(p)
	}
	return unsafe.SliceData(buf), C.size_t(len(polys))
}

func (a *cArena) environment(area Area) *C.planner_environment {
	env := (*C.planner_environment)(a.alloc(C.sizeof_planner_environment))
	env.perimeter = a.line(area.Perimeter)
	env.obstacles, env.obstacle_count = a.lines(area.Exclusions)
	env.mow_areas, env.mow_area_count = a.lines(area.MowAreas)
	env.virtual_wire = a.line(area.SearchWire)
	return env
}

func cPattern(p Pattern) (C.planner_pattern, error) {
	switch p {
	case PatternLines:
		return C.PLANNER_PATTERN_LINES, nil
	case PatternSquares:
		return C.PLANNER_PATTERN_SQUARES, nil
	case PatternRings:
		return C.PLANNER_PATTERN_RINGS, nil
	}
	return 0, fmt.Errorf("%w: unknown pattern %q", ErrInvalid, p)
}

func laps(n int) (C.size_t, error) {
	if n < 0 || n > math.MaxInt32 {
		return 0, fmt.Errorf("%w: laps must not be negative, got %d", ErrInvalid, n)
	}
	return C.size_t(n), nil
}

func route(area Area, s Settings, start geo.Point) ([]geo.Point, error) {
	pattern, err := cPattern(s.Pattern)
	if err != nil {
		return nil, err
	}
	borderLaps, err := laps(s.BorderLaps)
	if err != nil {
		return nil, err
	}
	exclusionLaps, err := laps(s.ExclusionLaps)
	if err != nil {
		return nil, err
	}
	var a cArena
	defer a.free()
	cs := (*C.planner_settings)(a.alloc(C.sizeof_planner_settings))
	*cs = C.planner_settings{
		pattern:                   pattern,
		offset:                    C.double(s.LaneWidthM),
		angle:                     C.double(s.AngleRad),
		distance_to_border:        C.double(s.DistanceToBorderM),
		mow_area:                  C.bool(s.MowArea),
		mow_border:                C.bool(s.BorderLaps > 0),
		mow_border_ccw:            C.bool(s.BorderCCW),
		border_laps:               borderLaps,
		mow_exclusions_border:     C.bool(s.ExclusionLaps > 0),
		mow_exclusions_border_ccw: C.bool(s.ExclusionsCCW),
		exclusions_border_laps:    exclusionLaps,
	}
	env := a.environment(area)
	return call(&a, func(out *C.planner_path, msg *C.char, n C.size_t) C.planner_status {
		return C.planner_compute(env, cs, cPoint(start), out, msg, n)
	})
}

func way(area Area, start, goal geo.Point) ([]geo.Point, error) {
	var a cArena
	defer a.free()
	env := a.environment(area)
	return call(&a, func(out *C.planner_path, msg *C.char, n C.size_t) C.planner_status {
		return C.planner_find_path(env, cPoint(start), cPoint(goal), out, msg, n)
	})
}

func cPoint(p geo.Point) C.planner_point {
	return C.planner_point{x: C.double(p.X), y: C.double(p.Y)}
}

const msgLen = 256

// call runs one C API function and turns its result into Go values.
func call(a *cArena, f func(out *C.planner_path, msg *C.char, n C.size_t) C.planner_status) ([]geo.Point, error) {
	out := (*C.planner_path)(a.alloc(C.sizeof_planner_path))
	msg := (*C.char)(a.alloc(msgLen))
	status := f(out, msg, msgLen)
	defer C.planner_free_path(out)
	text := C.GoString(msg)
	switch status {
	case C.PLANNER_OK:
	case C.PLANNER_INVALID_INPUT:
		return nil, fmt.Errorf("%w: %s", ErrInvalid, text)
	case C.PLANNER_NO_PATH:
		return nil, ErrNoPath
	default:
		return nil, fmt.Errorf("%w: %s", ErrFailed, text)
	}
	src := unsafe.Slice(out.points, int(out.count))
	pts := make([]geo.Point, len(src))
	for i, p := range src {
		pts[i] = geo.Point{X: float64(p.x), Y: float64(p.y)}
	}
	return pts, nil
}
