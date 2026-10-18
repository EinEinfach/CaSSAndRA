//go:build cpp

// The C++ planner, compiled by cgo together with cgo.go (build tag cpp).
// Only the sources the C API needs; GeoJSONReader, Visualizer and the Python
// wrapper stay out.
#include "../../third_party/PathPlannerCore/src/Geometry.cpp"
#include "../../third_party/PathPlannerCore/src/Environment.cpp"
#include "../../third_party/PathPlannerCore/src/PathPlanner.cpp"
#include "../../third_party/PathPlannerCore/src/PathService.cpp"
#include "../../third_party/PathPlannerCore/src/planner_c.cpp"
#include "../../third_party/PathPlannerCore/src/clipper2/clipper.engine.cpp"
#include "../../third_party/PathPlannerCore/src/clipper2/clipper.offset.cpp"
#include "../../third_party/PathPlannerCore/src/clipper2/clipper.rectclip.cpp"
#include "../../third_party/PathPlannerCore/src/clipper2/clipper.triangulation.cpp"
