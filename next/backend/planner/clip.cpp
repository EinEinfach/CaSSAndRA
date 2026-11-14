//go:build cpp

// Clips mow areas to the lawn (perimeter minus exclusions) with Clipper2
// (compiled in core.cpp), as legacy CaSSAndRA did with shapely. The planner
// needs this: rings and the distance to the border follow the mow area's own
// outline, so a selection over the border would put lanes outside the garden,
// and an exclusion across the outline leaves the rings empty. Exclusions
// fully inside stay holes, which the planner handles itself.
#include <cstdlib>
#include <exception>

#include "clipper2/clipper.h"
#include "planner_c.h"

namespace
{
    Clipper2Lib::PathD toPath(const planner_line &line)
    {
        Clipper2Lib::PathD path;
        path.reserve(line.count);
        for (size_t i = 0; i < line.count; ++i)
            path.emplace_back(line.points[i].x, line.points[i].y);
        return path;
    }

    // Copies paths (total points in all) into malloc'ed arrays for the Go side.
    int emit(const Clipper2Lib::PathsD &paths, size_t total,
             planner_point **out_points, size_t **out_counts, size_t *out_polys)
    {
        auto *pts = static_cast<planner_point *>(std::malloc(total * sizeof(planner_point)));
        auto *counts = static_cast<size_t *>(std::malloc(paths.size() * sizeof(size_t)));
        if (pts == nullptr || counts == nullptr)
        {
            std::free(pts);
            std::free(counts);
            return -1;
        }
        size_t k = 0;
        for (size_t i = 0; i < paths.size(); ++i)
        {
            counts[i] = paths[i].size();
            for (const auto &p : paths[i])
                pts[k++] = {p.x, p.y};
        }
        *out_points = pts;
        *out_counts = counts;
        *out_polys = paths.size();
        return 0;
    }
}

extern "C" int cassandra_clip_areas(planner_line perimeter, const planner_line *exclusions, size_t exclusion_count,
                                    const planner_line *areas, size_t area_count,
                                    planner_point **out_points, size_t **out_counts, size_t *out_polys)
{
    *out_points = nullptr;
    *out_counts = nullptr;
    *out_polys = 0;
    try
    {
        Clipper2Lib::PathsD subjects;
        for (size_t i = 0; i < area_count; ++i)
            subjects.push_back(toPath(areas[i]));
        Clipper2Lib::PathsD holes;
        for (size_t i = 0; i < exclusion_count; ++i)
            holes.push_back(toPath(exclusions[i]));
        Clipper2Lib::PathsD lawn = Clipper2Lib::Difference(
            Clipper2Lib::PathsD{toPath(perimeter)}, holes, Clipper2Lib::FillRule::NonZero, 3);
        // NonZero: a selection drawn around twice still counts once.
        Clipper2Lib::PathsD clipped = Clipper2Lib::Intersect(subjects, lawn, Clipper2Lib::FillRule::NonZero, 3);

        // Mow areas have no holes; the planner keeps out of exclusions anyway.
        Clipper2Lib::PathsD outer;
        size_t total = 0;
        for (auto &p : clipped)
        {
            if (p.size() >= 3 && Clipper2Lib::Area(p) > 0)
            {
                total += p.size();
                outer.push_back(std::move(p));
            }
        }
        if (outer.empty())
            return 0;
        return emit(outer, total, out_points, out_counts, out_polys);
    }
    catch (const std::exception &)
    {
        return -1;
    }
}

// Adds a figure to the lawn (perimeter minus exclusions) or cuts it out, as
// legacy CaSSAndRA did with shapely union/difference. Returns every ring of
// the result: outlines counter-clockwise (positive
// area), holes clockwise. An empty perimeter is an empty lawn.
extern "C" int cassandra_reshape_lawn(planner_line perimeter, const planner_line *exclusions, size_t exclusion_count,
                                      planner_line figure, int add,
                                      planner_point **out_points, size_t **out_counts, size_t *out_polys)
{
    *out_points = nullptr;
    *out_counts = nullptr;
    *out_polys = 0;
    try
    {
        const auto rule = Clipper2Lib::FillRule::NonZero;
        Clipper2Lib::PathsD lawn;
        if (perimeter.count >= 3)
        {
            Clipper2Lib::PathsD holes;
            for (size_t i = 0; i < exclusion_count; ++i)
                holes.push_back(toPath(exclusions[i]));
            lawn = Clipper2Lib::Difference(Clipper2Lib::PathsD{toPath(perimeter)}, holes, rule, 2);
        }
        // Union with nothing first: the figure counts once however it was drawn.
        Clipper2Lib::PathsD shape = Clipper2Lib::Union(Clipper2Lib::PathsD{toPath(figure)}, rule, 2);
        Clipper2Lib::PathsD result = add ? Clipper2Lib::Union(lawn, shape, rule, 2)
                                         : Clipper2Lib::Difference(lawn, shape, rule, 2);
        Clipper2Lib::PathsD rings;
        size_t total = 0;
        for (auto &p : result)
        {
            if (p.size() >= 3)
            {
                total += p.size();
                rings.push_back(std::move(p));
            }
        }
        if (rings.empty())
            return 0;
        return emit(rings, total, out_points, out_counts, out_polys);
    }
    catch (const std::exception &)
    {
        return -1;
    }
}
