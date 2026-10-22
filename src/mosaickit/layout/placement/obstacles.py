"""What a label must avoid, and how many of those things a rect hits."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mosaickit.layout.geometry import (
    Point,
    Rect,
    Segment,
    rect_hits_segment,
    rect_overlaps_polygon,
)
from mosaickit.layout.geometry.arrays import (
    SMALL,
    point_in_edges,
    polygon_array,
    rect_hits_segments,
    segment_array,
)

Polygons = tuple[tuple[Point, ...], ...]


@dataclass(frozen=True, slots=True)
class Obstacles:
    segments: tuple[Segment, ...] = ()
    rects: tuple[Rect, ...] = ()
    polygons: Polygons = ()

    def extended(
        self, *, segments: tuple[Segment, ...] = (), rects: tuple[Rect, ...] = ()
    ) -> Obstacles:
        return Obstacles(self.segments + segments, self.rects + rects, self.polygons)


@dataclass(frozen=True, slots=True)
class Placement:
    rect: Rect
    leader: Segment | None  # None for labels drawn without a leader
    violations: int


def count_violations(rect: Rect, obstacles: Obstacles, bounds: Rect, polygons: Polygons) -> int:
    """Hard-constraint failures: out of bounds, or touching a line, rect, or polygon.

    From :data:`~mosaickit.layout.geometry.arrays.SMALL` segments or polygon edges up
    the segment and polygon tests run on arrays; the count is the same.
    """
    if len(obstacles.segments) < SMALL and all(len(polygon) < SMALL for polygon in polygons):
        return _count_violations_loop(rect, obstacles, bounds, polygons)
    count = 0 if rect.within(bounds) else 1
    if obstacles.segments:
        count += int(np.count_nonzero(rect_hits_segments(rect, segment_array(obstacles.segments))))
    count += sum(1 for other in obstacles.rects if rect.intersects(other))
    count += sum(1 for polygon in polygons if _overlaps(rect, polygon))
    return count


def _count_violations_loop(
    rect: Rect, obstacles: Obstacles, bounds: Rect, polygons: Polygons
) -> int:
    count = 0 if rect.within(bounds) else 1
    count += sum(1 for a, b in obstacles.segments if rect_hits_segment(rect, a, b))
    count += sum(1 for other in obstacles.rects if rect.intersects(other))
    count += sum(1 for polygon in polygons if rect_overlaps_polygon(rect, polygon))
    return count


def _overlaps(rect: Rect, polygon: tuple[Point, ...]) -> bool:
    if len(polygon) < SMALL:
        return rect_overlaps_polygon(rect, polygon)
    edges = polygon_array(polygon)
    if any(point_in_edges(corner, edges) for corner in rect.corners()):
        return True
    return bool(np.any(rect_hits_segments(rect, edges)))
