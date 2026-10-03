"""Open space: connected free areas big enough to hold a callout unambiguously.

A small pocket enclosed by lines or regions (say, an unfilled strip between two
shaded regions) reads as an area of its own, so text placed there looks like it
names that pocket. Free areas smaller than ``MIN_FRACTION`` of the bounds are pockets.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from mosaickit.layout.geometry import Point, Rect, point_in_polygon
from mosaickit.layout.placement.obstacles import Obstacles

Cell = tuple[int, int]
MIN_FRACTION = 0.1


@dataclass(frozen=True, slots=True)
class OpenArea:
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


def open_area(bounds: Rect, obstacles: Obstacles, cell: float) -> OpenArea:
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
    return OpenArea(bounds, cell, frozenset(open_cells))
