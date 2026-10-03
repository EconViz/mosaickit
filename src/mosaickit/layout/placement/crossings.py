"""Keep a callout on its region's side of a crossing the region touches.

Where two lines properly cross at a point x on the region (both continue past x),
the lines diverge beyond x, away from the region. A label over there sits where
the lines extend rather than next to what it names, so the half-plane past x,
seen from the region's pole, is off limits.
"""

import math
from itertools import combinations

from mosaickit.layout.geometry import (
    Point,
    Polygon,
    Rect,
    Segment,
    distance_to_boundary,
    rect_hits_segment,
)


def _orient(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _proper_crossing(first: Segment, second: Segment) -> Point | None:
    """The crossing point when each segment passes strictly through the other."""
    (a, b), (c, d) = first, second
    if not (_orient(c, d, a) * _orient(c, d, b) < 0 and _orient(a, b, c) * _orient(a, b, d) < 0):
        return None
    rx, ry = b[0] - a[0], b[1] - a[1]
    sx, sy = d[0] - c[0], d[1] - c[1]
    t = ((c[0] - a[0]) * sy - (c[1] - a[1]) * sx) / (rx * sy - ry * sx)
    return (a[0] + t * rx, a[1] + t * ry)


def region_crossings(
    polygon: Polygon, segments: tuple[Segment, ...], *, tolerance: float
) -> tuple[Point, ...]:
    """Proper crossings of obstacle segments that lie on or within ``tolerance`` of the region."""
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    near = Rect(min(xs), min(ys), max(xs), max(ys)).inflate(tolerance)
    candidates = [s for s in segments if rect_hits_segment(near, *s)]
    found: list[Point] = []
    for first, second in combinations(candidates, 2):
        x = _proper_crossing(first, second)
        if x is not None and distance_to_boundary(x, polygon) <= tolerance:
            found.append(x)
    return tuple(found)


def beyond_crossings(point: Point, pole: Point, crossings: tuple[Point, ...]) -> int:
    """How many crossings ``point`` lies past, as seen from the pole."""
    count = 0
    for x in crossings:
        nx, ny = x[0] - pole[0], x[1] - pole[1]
        if math.hypot(nx, ny) == 0:
            continue
        if (point[0] - x[0]) * nx + (point[1] - x[1]) * ny > 0:
            count += 1
    return count
