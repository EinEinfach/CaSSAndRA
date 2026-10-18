//go:build cpp

// The C++ planner, compiled by cgo together with cgo.go (build tag cpp).
// Only the sources the C API needs; GeoJSONReader, Visualizer and the Python
// wrapper stay out.
//
// No fused multiply-add: compilers contract a*b+c differently per platform
// (clang on arm64 does, gcc on x86 cannot without FMA), and one rounding step
// can change the planner's choice of the next lane. Without it, every machine
// computes the same route as the tests. (cgo does not allow -ffp-contract=off.)
#if defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#elif defined(__GNUC__)
#pragma GCC optimize("fp-contract=off")
#endif
#include "../../third_party/PathPlannerCore/src/Geometry.cpp"
#include "../../third_party/PathPlannerCore/src/Environment.cpp"
#include "../../third_party/PathPlannerCore/src/PathPlanner.cpp"
#include "../../third_party/PathPlannerCore/src/PathService.cpp"
#include "../../third_party/PathPlannerCore/src/planner_c.cpp"
#include "../../third_party/PathPlannerCore/src/clipper2/clipper.engine.cpp"
#include "../../third_party/PathPlannerCore/src/clipper2/clipper.offset.cpp"
#include "../../third_party/PathPlannerCore/src/clipper2/clipper.rectclip.cpp"
#include "../../third_party/PathPlannerCore/src/clipper2/clipper.triangulation.cpp"
