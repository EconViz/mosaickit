"""Open space: connected free areas big enough to hold a callout unambiguously.

A small pocket enclosed by lines or regions (say, an unfilled strip between two
shaded regions) reads as an area of its own, so text placed there looks like it
names that pocket. Free areas smaller than ``MIN_FRACTION`` of the bounds are pockets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from mosaickit.layout.geometry import Point, Rect, polygon_edges
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


def _block_segments(blocked: np.ndarray, bounds: Rect, cell: float, segments: tuple) -> None:
    """Mark the cells each segment passes, sampled every half cell (``k / steps`` along it)."""
    cols, rows = blocked.shape
    steps = np.asarray(
        [max(1, math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / (cell / 2))) for a, b in segments],
        dtype=np.int64,
    )
    ends = np.asarray([(a[0], a[1], b[0], b[1]) for a, b in segments], dtype=float)
    owner = np.repeat(np.arange(len(segments)), steps + 1)
    first = np.cumsum(steps + 1) - (steps + 1)
    k = np.arange(len(owner)) - first[owner]
    t = k / steps[owner]
    ax, ay, bx, by = (ends[owner, i] for i in range(4))
    i = ((ax + (bx - ax) * t - bounds.x0) // cell).astype(np.int64)
    j = ((ay + (by - ay) * t - bounds.y0) // cell).astype(np.int64)
    keep = (i >= 0) & (i < cols) & (j >= 0) & (j < rows)
    blocked[i[keep], j[keep]] = True


def _block_polygon(blocked: np.ndarray, bounds: Rect, cell: float, polygon: tuple) -> None:
    """Mark the cells whose centre is inside the polygon (the ray-crossing test of
    :func:`~mosaickit.layout.geometry.point_in_polygon`, on the cells in its bounding box)."""
    cols, rows = blocked.shape
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    i0 = max(0, int((min(xs) - bounds.x0) // cell))
    i1 = min(cols, int((max(xs) - bounds.x0) // cell) + 1)
    j0 = max(0, int((min(ys) - bounds.y0) // cell))
    j1 = min(rows, int((max(ys) - bounds.y0) // cell) + 1)
    if i0 >= i1 or j0 >= j1:
        return
    cx = (bounds.x0 + (np.arange(i0, i1) + 0.5) * cell)[:, None]
    cy = (bounds.y0 + (np.arange(j0, j1) + 0.5) * cell)[None, :]
    inside = np.zeros((i1 - i0, j1 - j0), dtype=bool)
    for (x0, y0), (x1, y1) in polygon_edges(polygon):
        straddles = (y0 > cy) != (y1 > cy)
        if not straddles.any():
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            crossing = cx < x0 + (cy - y0) * (x1 - x0) / (y1 - y0)
        inside ^= straddles & crossing
    blocked[i0:i1, j0:j1] |= inside


def _runs(blocked: np.ndarray) -> list[list[tuple[int, int]]]:
    """Per column, the ``[start, end)`` runs of free cells."""
    found: list[list[tuple[int, int]]] = []
    for column in blocked:
        free = np.concatenate(([False], ~column, [False]))
        edges = np.flatnonzero(free[1:] != free[:-1])
        found.append(list(zip(edges[::2].tolist(), edges[1::2].tolist(), strict=True)))
    return found


def _components(blocked: np.ndarray) -> list[tuple[int, list[tuple[int, int, int]]]]:
    """Connected free areas (4-neighbour) as ``(cell count, [(column, start, end), ...])``."""
    columns = _runs(blocked)
    parent: list[int] = []
    owner: list[tuple[int, int, int]] = []
    ids: list[list[int]] = []

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, runs in enumerate(columns):
        ids.append([])
        for start, end in runs:
            index = len(parent)
            parent.append(index)
            owner.append((i, start, end))
            ids[i].append(index)
        if i == 0:
            continue
        for index, (start, end) in zip(ids[i], runs, strict=True):
            for other, (s, e) in zip(ids[i - 1], columns[i - 1], strict=True):
                if s < end and start < e:
                    parent[find(other)] = find(index)
    groups: dict[int, list[tuple[int, int, int]]] = {}
    for index, run in enumerate(owner):
        groups.setdefault(find(index), []).append(run)
    return [(sum(e - s for _, s, e in runs), runs) for runs in groups.values()]


def open_area(bounds: Rect, obstacles: Obstacles, cell: float) -> OpenArea:
    cols = max(1, math.ceil(bounds.width / cell))
    rows = max(1, math.ceil(bounds.height / cell))
    blocked = np.zeros((cols, rows), dtype=bool)
    if obstacles.segments:
        _block_segments(blocked, bounds, cell, obstacles.segments)
    for rect in obstacles.rects:
        i0 = int((rect.x0 - bounds.x0) // cell)
        j0 = int((rect.y0 - bounds.y0) // cell)
        i1 = int((rect.x1 - bounds.x0) // cell)
        j1 = int((rect.y1 - bounds.y0) // cell)
        blocked[max(0, i0) : max(0, i1 + 1), max(0, j0) : max(0, j1 + 1)] = True
    for polygon in obstacles.polygons:
        _block_polygon(blocked, bounds, cell, polygon)
    minimum = MIN_FRACTION * cols * rows
    open_cells: set[Cell] = set()
    for size, runs in _components(blocked):
        if size >= minimum:
            open_cells.update((i, j) for i, start, end in runs for j in range(start, end))
    return OpenArea(bounds, cell, frozenset(open_cells))
