"""What a label must avoid, and how many of those things a rect hits."""

from __future__ import annotations

from dataclasses import dataclass

from mosaickit.layout.geometry import (
    Point,
    Rect,
    Segment,
    rect_hits_segment,
    rect_overlaps_polygon,
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
    """Hard-constraint failures: out of bounds, or touching a line, rect, or polygon."""
    count = 0 if rect.within(bounds) else 1
    count += sum(1 for a, b in obstacles.segments if rect_hits_segment(rect, a, b))
    count += sum(1 for other in obstacles.rects if rect.intersects(other))
    count += sum(1 for polygon in polygons if rect_overlaps_polygon(rect, polygon))
    return count
