"""The positions a label may take: preferred sides first, then rings or rows further out."""

from __future__ import annotations

import math
from dataclasses import dataclass

from mosaickit.layout.geometry import Point, Rect
from mosaickit.layout.labels.model import Label
from mosaickit.layout.labels.options import COMPASS, LabelOptions

_DIAGONAL = 1 / math.sqrt(2)
COMPASS_UNITS: dict[str, Point] = {
    "right": (1.0, 0.0),
    "upper-right": (_DIAGONAL, _DIAGONAL),
    "above": (0.0, 1.0),
    "upper-left": (-_DIAGONAL, _DIAGONAL),
    "left": (-1.0, 0.0),
    "lower-left": (-_DIAGONAL, -_DIAGONAL),
    "below": (0.0, -1.0),
    "lower-right": (_DIAGONAL, -_DIAGONAL),
}
"""Unit direction of each side (y up)."""

OPPOSITE = {
    "right": "left",
    "left": "right",
    "above": "below",
    "below": "above",
    "upper-right": "lower-left",
    "lower-left": "upper-right",
    "upper-left": "lower-right",
    "lower-right": "upper-left",
}

TEXT_ANCHOR = {
    (1, 0): "left",
    (-1, 0): "right",
    (0, 1): "bottom",
    (0, -1): "top",
    (1, 1): "bottom-left",
    (-1, 1): "bottom-right",
    (1, -1): "top-left",
    (-1, -1): "top-right",
    (0, 0): "center",
}
"""``TextLayer.anchor`` that puts the text on the side with signs ``(sx, sy)`` of its point."""

_TAN_HALF_OCTANT = math.tan(math.pi / 8)  # where a direction changes octant


@dataclass(frozen=True, slots=True)
class Candidate:
    """One position: the box, its offset from the anchor and what it costs on its own."""

    side: str
    signs: tuple[int, int]
    offset: Point
    box: Rect
    distance: float
    rank: float
    leader_needed: bool

    @property
    def text_anchor(self) -> str:
        return TEXT_ANCHOR[self.signs]


def _step(major: float, minor: float) -> int:
    if abs(major) < _TAN_HALF_OCTANT * abs(minor):
        return 0
    return 1 if major > 0 else -1 if major < 0 else 0


def _box(anchor: Point, offset: Point, signs: tuple[int, int], size: tuple[float, float]) -> Rect:
    """The ``size`` box whose near edge or corner (by ``signs``) sits at anchor + offset."""
    px, py = anchor[0] + offset[0], anchor[1] + offset[1]
    width, height = size
    x0 = px if signs[0] > 0 else px - width if signs[0] < 0 else px - width / 2
    y0 = py if signs[1] > 0 else py - height if signs[1] < 0 else py - height / 2
    return Rect(x0, y0, x0 + width, y0 + height)


def _make(
    label: Label, side: str, signs: tuple[int, int], offset: Point, rank: float, o: LabelOptions
) -> Candidate:
    box = _box(label.anchor, offset, signs, label.size)
    return Candidate(
        side, signs, offset, box, math.hypot(*offset), rank, math.hypot(*offset) > o.leader_after
    )


def _signs(side: str) -> tuple[int, int]:
    ux, uy = COMPASS_UNITS[side]
    return (_step(ux, uy), _step(uy, ux))


def _nearest_side(ux: float, uy: float) -> str:
    return max(COMPASS, key=lambda s: COMPASS_UNITS[s][0] * ux + COMPASS_UNITS[s][1] * uy)


def _ring_candidates(label: Label, o: LabelOptions) -> list[Candidate]:
    order = {side: i for i, side in enumerate(label.sides)}
    found: list[Candidate] = []
    for ring in range(o.rings + 1):
        distance = o.gap + ring * o.ring_step
        for side in label.sides:
            sx, sy = _signs(side)
            offset = (sx * distance, sy * distance)
            found.append(_make(label, side, (sx, sy), offset, float(order[side]), o))
        for k in range(o.ring_directions):
            angle = 2 * math.pi * (k + 0.5) / o.ring_directions
            ux, uy = math.cos(angle), math.sin(angle)
            side = _nearest_side(ux, uy)
            if side not in order:
                continue
            signs = (_step(ux, uy), _step(uy, ux))
            found.append(
                _make(
                    label,
                    side,
                    signs,
                    (ux * distance, uy * distance),
                    order[side] + o.extra_rank,
                    o,
                )
            )
    return found


def _stack_candidates(label: Label, o: LabelOptions) -> list[Candidate]:
    sides = tuple(s for s in label.sides if s in ("above", "below", "left", "right"))
    if not o.tick_strategy.endswith("opposite"):
        sides = sides[:1]
    rows = o.stack_rows if o.tick_strategy.startswith("stagger") else 0
    found: list[Candidate] = []
    for index, side in enumerate(sides):
        ux, uy = COMPASS_UNITS[side]
        extent = label.size[1] if ux == 0 else label.size[0]
        for row in range(rows + 1):
            distance = o.gap + row * (extent + o.row_gap)
            found.append(
                _make(
                    label,
                    side,
                    _signs(side),
                    (ux * distance, uy * distance),
                    float(index * (rows + 1) + row),
                    o,
                )
            )
    return found


def base_cost(candidate: Candidate, options: LabelOptions) -> float:
    """Cost of a position from its rank and distance alone (leaders are added elsewhere)."""
    return candidate.rank * options.rank_weight + candidate.distance * options.distance_weight


def candidates_for(label: Label, options: LabelOptions) -> list[Candidate]:
    """Every position of ``label``, in generation order (preferred first)."""
    if label.spread == "stack":
        return _stack_candidates(label, options)
    return _ring_candidates(label, options)
