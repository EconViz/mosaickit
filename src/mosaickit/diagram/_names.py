"""Collision-aware placement of curve names, built on :mod:`mosaickit.layout`."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from mosaickit.layout import Obstacles, Rect
from mosaickit.layout.placement.obstacles import count_violations

Point = tuple[float, float]

SIDES: dict[str, tuple[int, int, str]] = {
    "right": (1, 0, "left"),
    "left": (-1, 0, "right"),
    "above": (0, 1, "bottom"),
    "below": (0, -1, "top"),
    "upper-right": (1, 1, "bottom-left"),
    "lower-right": (1, -1, "top-left"),
    "upper-left": (-1, 1, "bottom-right"),
    "lower-left": (-1, -1, "top-right"),
}
"""Each side as ``(sign x, sign y, TextLayer anchor)``; the anchor puts the text on that side."""

DEFAULT_NAME_ORDER = (
    "lower-right",
    "upper-left",
    "lower-left",
    "upper-right",
    "right",
    "left",
    "above",
    "below",
)
"""Where a curve's name goes off its end, first choice first."""

RISING_NAME_ORDER = (
    "upper-right",
    "right",
    "lower-right",
    "above",
    "upper-left",
    "lower-left",
    "left",
    "below",
)
"""The same, for a rising curve when its name should sit above its end."""

TEX_LAYOUT_COMMANDS = ("left", "right", "frac", "dfrac")
"""TeX commands that draw no glyph of their own; pass as ``strip_commands`` to leave them out."""

TextSize = Callable[[str, float], Point]
"""Estimates the ``(width, height)`` in points of a label set at a font size in points."""


@dataclass(frozen=True, slots=True)
class NamePlacement:
    """Where a name goes: the :data:`SIDES` key, the offset in points and the box."""

    side: str
    offset: Point
    box: Rect


def candidate(
    anchor: Point, side: str, size: Point, gap: float, diagonal: float = 1.0
) -> NamePlacement:
    """The box of a ``size`` text on ``side`` of ``anchor``, ``gap`` points away
    (``gap * diagonal`` on a diagonal side)."""
    sx, sy, _ = SIDES[side]
    width, height = size
    distance = gap * diagonal if sx and sy else gap
    x0 = anchor[0] + sx * distance - (0 if sx > 0 else width if sx < 0 else width / 2)
    y0 = anchor[1] + sy * distance - (0 if sy > 0 else height if sy < 0 else height / 2)
    return NamePlacement(
        side, (sx * distance, sy * distance), Rect(x0, y0, x0 + width, y0 + height)
    )


def place_name(
    anchor: Point,
    size: Point,
    obstacles: Obstacles,
    bounds: Rect,
    order: Sequence[str],
    *,
    gap: float,
    clearance: float,
    diagonal: float = 1.0,
) -> NamePlacement:
    """The first side of ``order`` whose box touches nothing, else the one touching least."""
    best: tuple[int, NamePlacement] | None = None
    for side in order:
        placement = candidate(anchor, side, size, gap, diagonal)
        probe = placement.box.inflate(clearance)
        violations = count_violations(probe, obstacles, bounds, obstacles.polygons)
        if violations == 0:
            return placement
        if best is None or violations < best[0]:
            best = (violations, placement)
    assert best is not None
    return best[1]
