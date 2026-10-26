"""Array forms of the segment and polygon tests, for inputs with many segments.

NumPy's fixed cost per call outweighs the Python loops below about 30 segments, so
callers use these from :data:`SMALL` segments or polygon edges up and keep the loops
below that. Every test applies the arithmetic of its scalar counterpart (the same
orientation products, the same ray-crossing parity), so the counts, and the label
positions chosen from them, are those of the loops.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from mosaickit.layout.geometry.polygon import polygon_edges
from mosaickit.layout.geometry.rect import Point, Rect

SMALL = 32


class _ArrayCache:
    """Arrays of segment and polygon tuples, keyed by the tuple object itself.

    The same tuple of obstacles is tested against many candidate rects, so its array
    is built once. An entry holds a reference to its tuple, which keeps the ``id`` valid.
    """

    def __init__(self, limit: int = 256) -> None:
        self.limit = limit
        self._arrays: dict[int, tuple[object, np.ndarray]] = {}

    def get(self, owner: Any, build: Any) -> np.ndarray:
        cached = self._arrays.get(id(owner))
        if cached is not None and cached[0] is owner:
            return cached[1]
        if len(self._arrays) > self.limit:
            self._arrays.clear()
        array = build(owner)
        self._arrays[id(owner)] = (owner, array)
        return array


_cache = _ArrayCache()


def segment_array(segments: Any) -> np.ndarray:
    """``(n, 4)`` rows ``(ax, ay, bx, by)`` of a tuple of segments."""
    return _cache.get(
        segments,
        lambda s: np.asarray([(a[0], a[1], b[0], b[1]) for a, b in s], dtype=float).reshape(-1, 4),
    )


def polygon_array(polygon: Any) -> np.ndarray:
    """``(n, 4)`` rows of the edges of a polygon, as :func:`polygon_edges` lists them."""
    return _cache.get(
        polygon,
        lambda p: np.asarray(
            [(a[0], a[1], b[0], b[1]) for a, b in polygon_edges(p)], dtype=float
        ).reshape(-1, 4),
    )


def _orient(ax, ay, bx, by, cx, cy):  # type: ignore[no-untyped-def]
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def _on_segment(ax, ay, bx, by, px, py):  # type: ignore[no-untyped-def]
    return (
        (np.minimum(ax, bx) <= px)
        & (px <= np.maximum(ax, bx))
        & (np.minimum(ay, by) <= py)
        & (py <= np.maximum(ay, by))
    )


def segments_intersect_many(ax, ay, bx, by, cx, cy, dx, dy):  # type: ignore[no-untyped-def]
    """:func:`segments_intersect` of ``ab`` against ``cd`` for broadcastable arrays."""
    d1 = _orient(cx, cy, dx, dy, ax, ay)
    d2 = _orient(cx, cy, dx, dy, bx, by)
    d3 = _orient(ax, ay, bx, by, cx, cy)
    d4 = _orient(ax, ay, bx, by, dx, dy)
    hit = ((d1 * d2) < 0) & ((d3 * d4) < 0)
    # the touching cases only matter where an orientation is exactly zero
    for d, (px, py, qx, qy, rx, ry) in (
        (d1, (cx, cy, dx, dy, ax, ay)),
        (d2, (cx, cy, dx, dy, bx, by)),
        (d3, (ax, ay, bx, by, cx, cy)),
        (d4, (ax, ay, bx, by, dx, dy)),
    ):
        zero = d == 0
        if np.any(zero):
            hit = hit | (zero & _on_segment(px, py, qx, qy, rx, ry))
    return hit


def rect_hits_segments(rect: Rect, array: np.ndarray) -> np.ndarray:
    """:func:`rect_hits_segment` of ``rect`` for every row ``(ax, ay, bx, by)``."""
    ax, ay, bx, by = array[:, 0], array[:, 1], array[:, 2], array[:, 3]
    hit = ((rect.x0 <= ax) & (ax <= rect.x1) & (rect.y0 <= ay) & (ay <= rect.y1)) | (
        (rect.x0 <= bx) & (bx <= rect.x1) & (rect.y0 <= by) & (by <= rect.y1)
    )
    edges = np.asarray([(p[0], p[1], q[0], q[1]) for p, q in rect.edges()], dtype=float)
    px, py, qx, qy = (edges[:, i, None] for i in range(4))
    return hit | segments_intersect_many(ax, ay, bx, by, px, py, qx, qy).any(axis=0)


def point_in_edges(point: Point, edges: np.ndarray) -> bool:
    """:func:`point_in_polygon` for a polygon given as its edge array."""
    x, y = point
    x0, y0, x1, y1 = edges[:, 0], edges[:, 1], edges[:, 2], edges[:, 3]
    straddles = (y0 > y) != (y1 > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        crossing = x < x0 + (y - y0) * (x1 - x0) / (y1 - y0)
    return bool(np.count_nonzero(straddles & crossing) % 2)
