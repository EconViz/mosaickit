"""A curly brace outline over a span, built from four quarter arcs."""

from __future__ import annotations

import math
from dataclasses import dataclass

from mosaickit.layout.geometry.rect import Point


@dataclass(frozen=True, slots=True)
class Brace:
    points: tuple[Point, ...]
    tip: Point


def _arc(cx: float, cy: float, radius: float, a0: float, a1: float, samples: int) -> list[Point]:
    return [
        (
            cx + radius * math.cos(math.radians(a0 + (a1 - a0) * i / samples)),
            cy + radius * math.sin(math.radians(a0 + (a1 - a0) * i / samples)),
        )
        for i in range(samples + 1)
    ]


def brace_outline(
    start: float,
    end: float,
    *,
    base: float,
    depth: float,
    direction: int,
    axis: str = "y",
    samples: int = 12,
) -> Brace:
    """A brace over ``start``..``end`` along an axis, its ends on the line ``base``.

    The tip sits at the middle of the span, ``depth`` past ``base`` in ``direction``
    (+1 or -1). On the ``"y"`` axis points are ``(across, along)``; on ``"x"`` they
    are ``(along, across)``. Spans shorter than twice the depth get smaller arcs.
    """
    if start == end:
        raise ValueError("A brace needs a non-empty span")
    if not depth > 0:
        raise ValueError("Brace depth must be positive")
    if direction not in (1, -1):
        raise ValueError("Brace direction must be +1 or -1")
    if axis not in ("x", "y"):
        raise ValueError(f"Unknown axis: {axis!r}")
    lo, hi = min(start, end), max(start, end)
    radius = min(depth / 2, (hi - lo) / 4)
    middle = (lo + hi) / 2
    # Local frame: u across the axis (0 on the base line), v along it.
    local = (
        _arc(0, lo + radius, radius, -90, 0, samples)
        + _arc(2 * radius, middle - radius, radius, 180, 90, samples)
        # The middle arcs meet at the tip; drop the shared point.
        + _arc(2 * radius, middle + radius, radius, 270, 180, samples)[1:]
        + _arc(0, hi - radius, radius, 0, 90, samples)
    )
    # Stretch across so the tip reaches the full depth even when the arcs shrank.
    stretch = depth / (2 * radius)
    oriented = [(base + direction * u * stretch, v) for u, v in local]
    tip = (base + direction * depth, middle)
    if axis == "x":
        return Brace(tuple((v, u) for u, v in oriented), (tip[1], tip[0]))
    return Brace(tuple(oriented), tip)
