"""Axis-aligned rectangles and the coordinate aliases used by layout.

Layout coordinates are display pixels.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

Point = tuple[float, float]
Segment = tuple[Point, Point]
Polygon = Sequence[Point]


@dataclass(frozen=True, slots=True)
class Rect:
    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def centered(cls, center: Point, width: float, height: float) -> Rect:
        cx, cy = center
        return cls(cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2)

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def center(self) -> Point:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)

    def inflate(self, pad: float) -> Rect:
        return Rect(self.x0 - pad, self.y0 - pad, self.x1 + pad, self.y1 + pad)

    def corners(self) -> tuple[Point, Point, Point, Point]:
        return ((self.x0, self.y0), (self.x1, self.y0), (self.x1, self.y1), (self.x0, self.y1))

    def edges(self) -> tuple[Segment, ...]:
        corners = self.corners()
        return tuple((corners[i], corners[(i + 1) % 4]) for i in range(4))

    def contains(self, point: Point) -> bool:
        x, y = point
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def within(self, other: Rect) -> bool:
        return (
            other.x0 <= self.x0
            and other.y0 <= self.y0
            and self.x1 <= other.x1
            and self.y1 <= other.y1
        )

    def intersects(self, other: Rect) -> bool:
        return not (
            self.x1 < other.x0 or other.x1 < self.x0 or self.y1 < other.y0 or other.y1 < self.y0
        )

    def nearest_point(self, point: Point) -> Point:
        x, y = point
        return (min(max(x, self.x0), self.x1), min(max(y, self.y0), self.y1))
