"""The greedy callout search and the cell-by-cell open area as they were before the array
rewrite. Tests compare the current implementation with these on random scenes."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from mosaickit.layout.geometry import (
    Point,
    Polygon,
    Rect,
    Segment,
    point_in_polygon,
    polylabel,
    ray_exit,
)
from mosaickit.layout.placement.candidates import anchored_rect, direction
from mosaickit.layout.placement.crossings import beyond_crossings, region_crossings
from mosaickit.layout.placement.leader import build_leader, leader_violations
from mosaickit.layout.placement.obstacles import Obstacles, Placement, count_violations

Cell = tuple[int, int]
MIN_FRACTION = 0.1


@dataclass(frozen=True, slots=True)
class ReferenceOpenArea:
    bounds: Rect
    cell: float
    cells: frozenset[Cell]

    def contains(self, point: Point) -> bool:
        return self._cell_of(point) in self.cells

    def _cell_of(self, point: Point) -> Cell:
        return (
            int((point[0] - self.bounds.x0) // self.cell),
            int((point[1] - self.bounds.y0) // self.cell),
        )


def reference_open_area(bounds: Rect, obstacles: Obstacles, cell: float) -> ReferenceOpenArea:
    cols = max(1, math.ceil(bounds.width / cell))
    rows = max(1, math.ceil(bounds.height / cell))

    def cell_of(x: float, y: float) -> Cell:
        return (int((x - bounds.x0) // cell), int((y - bounds.y0) // cell))

    def center(i: int, j: int) -> Point:
        return (bounds.x0 + (i + 0.5) * cell, bounds.y0 + (j + 0.5) * cell)

    blocked: set[Cell] = set()
    for (ax, ay), (bx, by) in obstacles.segments:
        steps = max(1, math.ceil(math.hypot(bx - ax, by - ay) / (cell / 2)))
        for k in range(steps + 1):
            t = k / steps
            blocked.add(cell_of(ax + (bx - ax) * t, ay + (by - ay) * t))
    for rect in obstacles.rects:
        i0, j0 = cell_of(rect.x0, rect.y0)
        i1, j1 = cell_of(rect.x1, rect.y1)
        blocked.update((i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1))
    for polygon in obstacles.polygons:
        i0, j0 = cell_of(min(p[0] for p in polygon), min(p[1] for p in polygon))
        i1, j1 = cell_of(max(p[0] for p in polygon), max(p[1] for p in polygon))
        for i in range(max(0, i0), min(cols, i1 + 1)):
            for j in range(max(0, j0), min(rows, j1 + 1)):
                if point_in_polygon(center(i, j), polygon):
                    blocked.add((i, j))

    seen: set[Cell] = set()
    open_cells: set[Cell] = set()
    minimum = MIN_FRACTION * cols * rows
    for i in range(cols):
        for j in range(rows):
            if (i, j) in blocked or (i, j) in seen:
                continue
            component = {(i, j)}
            queue = deque([(i, j)])
            seen.add((i, j))
            while queue:
                ci, cj = queue.popleft()
                for ni, nj in ((ci + 1, cj), (ci - 1, cj), (ci, cj + 1), (ci, cj - 1)):
                    neighbour = (ni, nj)
                    if (
                        0 <= ni < cols
                        and 0 <= nj < rows
                        and neighbour not in blocked
                        and neighbour not in seen
                    ):
                        seen.add(neighbour)
                        component.add(neighbour)
                        queue.append(neighbour)
            if len(component) >= minimum:
                open_cells |= component
    return ReferenceOpenArea(bounds, cell, frozenset(open_cells))


DIRECTIONS = 16
GAPS = (12.0, 24.0, 40.0)
FAR_GAPS = (60.0, 90.0)
LEADER_GAP = 2.0
OPEN_AREA_CELL = 4.0
CROSSING_TOLERANCE = 1.5  # px


def reference_place_callout(
    polygon: Polygon,
    size: tuple[float, float],
    obstacles: Obstacles,
    bounds: Rect,
    *,
    scale: float = 1.0,
) -> Placement:
    """Best callout position. ``scale`` converts the point-based gaps to pixels."""
    own = tuple(polygon)
    pole = polylabel(own)
    # The label may never cover its own region, even when it is not an obstacle.
    polygons = obstacles.polygons if own in obstacles.polygons else (*obstacles.polygons, own)
    everything = Obstacles(obstacles.segments, obstacles.rects, polygons)
    area = reference_open_area(bounds, everything, OPEN_AREA_CELL * scale)
    crossings = region_crossings(own, obstacles.segments, tolerance=CROSSING_TOLERANCE)
    best: tuple[tuple[int, float], Placement] | None = None
    for gaps in (GAPS, FAR_GAPS):
        for k in range(DIRECTIONS):
            unit = direction(k, DIRECTIONS)
            exit_distance = ray_exit(pole, unit, own)
            for gap in gaps:
                rect = anchored_rect(pole, unit, exit_distance + gap * scale, size)
                leader = build_leader(pole, rect, LEADER_GAP * scale)
                violations = (
                    count_violations(rect, obstacles, bounds, polygons)
                    + (0 if area.contains(rect.center) else 1)
                    + leader_violations(leader, everything, own)
                    + beyond_crossings(rect.center, pole, crossings)
                )
                key = (violations, math.dist(*leader))
                if best is None or key < best[0]:
                    best = (key, Placement(rect, leader, violations))
        assert best is not None
        if best[1].violations == 0:
            break
    assert best is not None
    return best[1]


def follow_leader(leader: Segment, rect: Rect, *, scale: float = 1.0) -> Segment:
    """``leader`` redrawn from its start to ``rect``, after the label it points at moved."""
    return build_leader(leader[0], rect, LEADER_GAP * scale)
