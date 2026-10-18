"""Writes golden.json: routes and ways for garden.json, computed with the
planner's Python module (pybind11) - an independent way into the same C++ core
than the Go binding under test.

Run with the module of the pinned planner on the path, e.g.:
  cmake -S ../../../../third_party/PathPlannerCore -B /tmp/pp && cmake --build /tmp/pp --target coverage_path_planner
  PYTHONPATH=/tmp/pp python3 make_golden.py
"""
import json
import os

import coverage_path_planner as cpp

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "garden.json")) as f:
    garden = json.load(f)


def poly(pts):
    return cpp.Polygon([cpp.Point(x, y) for x, y in pts])


def env(mow_areas=()):
    e = cpp.Environment(poly(garden["perimeter"]))
    for ex in garden["exclusions"]:
        e.addObstacle(poly(ex))
    for a in mow_areas:
        e.addMowArea(poly(a))
    wire = cpp.LineString()
    for x, y in garden["searchWire"]:
        wire.addPoint(cpp.Point(x, y))
    e.setVirtualWire(wire)
    return e


out = {"version": cpp.PathService().getVersion(), "routes": []}
for r in garden["routes"]:
    s = r["settings"]
    ps = cpp.PathSettings()
    ps.pattern = s["pattern"]
    ps.offset = s["laneWidthM"]
    ps.angle = s["angleRad"]
    ps.distanceToBorder = s["distanceToBorderM"]
    ps.mowArea = s["mowArea"]
    ps.mowBorder = s["borderLaps"] > 0
    ps.borderLaps = s["borderLaps"]
    ps.mowBorderCcw = s["borderCcw"]
    ps.mowExclusionsBorder = s["exclusionLaps"] > 0
    ps.exclusionsBorderLaps = s["exclusionLaps"]
    ps.mowExclusionsBorderCcw = s["exclusionsCcw"]
    res = cpp.PathService().computeFullTask(env(r.get("mowAreas", [])), ps, cpp.Point(*r["start"]))
    out["routes"].append({"name": r["name"], "path": [[p.x, p.y] for p in res.path.getPoints()]})

with open(os.path.join(here, "golden.json"), "w") as f:
    json.dump(out, f, indent=1)
