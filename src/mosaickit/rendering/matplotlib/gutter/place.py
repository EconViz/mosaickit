"""Turn measured axis layers into gutter positions using the pure layout modules.

Outward from the axis: marks, then outside braces (one column per lane), then
notes. Marks and notes are each spread along the axis so none overlap.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from mosaickit.layout.geometry import Brace, Point, brace_outline
from mosaickit.layout.gutter import gutter_columns
from mosaickit.layout.stack1d import assign_lanes, spread
from mosaickit.rendering.matplotlib.gutter.frame import AxisFrame

AXIS_GAP = 5.0  # pt between the axis and the first column
COLUMN_GAP = 8.0  # pt between columns
MARK_GAP = 2.0  # pt between neighbouring marks
NOTE_GAP = 4.0  # pt between neighbouring notes
BRACE_DEPTH = 8.0  # pt from a brace's ends to its tip
LABEL_GAP = 3.0  # pt between a brace tip and its label
INSIDE_GAP = 3.0  # pt between the axis and an inside brace
LANE_GAP = 2.0  # pt kept between braces sharing a lane


@dataclass(frozen=True, slots=True)
class GutterText:
    """Text whose axis-facing side sits at ``anchor``."""

    resolved: Any
    text: str
    anchor: Point
    gid: str


@dataclass(frozen=True, slots=True)
class PlacedBrace:
    resolved: Any
    outline: Brace
    reach: float  # how far, in px, an inside label may slide from the tip along the axis


@dataclass(frozen=True, slots=True)
class Item:
    """One axis layer with its text and that text's ``(width, height)`` in px."""

    resolved: Any
    text: str | None
    size: tuple[float, float]


@dataclass(frozen=True, slots=True)
class GutterPlan:
    texts: tuple[GutterText, ...]
    braces: tuple[PlacedBrace, ...]
    inside: tuple[PlacedBrace, ...]  # labels still to be placed beside the tip


def _span(ax: Any, frame: AxisFrame, layer: Any) -> tuple[float, float]:
    a, b = frame.along(ax, layer.start), frame.along(ax, layer.end)
    return min(a, b), max(a, b)


def _spread_column(
    ax: Any, frame: AxisFrame, items: Sequence[Item], near: float, gap: float
) -> list[GutterText]:
    alongs = [frame.along(ax, item.resolved.layer.value) for item in items]
    sizes = [frame.split(item.size)[0] for item in items]
    placed = spread(alongs, sizes, gap)
    return [
        GutterText(item.resolved, item.text or "", frame.point(along, near), item.resolved.layer.id)
        for item, along in zip(items, placed, strict=True)
    ]


def plan_gutter(
    ax: Any,
    frame: AxisFrame,
    marks: Sequence[Item],
    braces: Sequence[Item],
    notes: Sequence[Item],
    scale: float,
) -> GutterPlan:
    """Positions for one axis's gutter. ``scale`` converts pt to px."""
    outside = [b for b in braces if b.resolved.layer.side == "outside"]
    inside = [b for b in braces if b.resolved.layer.side == "inside"]
    depth, label_gap = BRACE_DEPTH * scale, LABEL_GAP * scale

    # Outside braces share a lane unless their spans or labels would touch.
    extents = []
    for item in outside:
        lo, hi = _span(ax, frame, item.resolved.layer)
        half = frame.split(item.size)[0] / 2 if item.text else 0.0
        middle = (lo + hi) / 2
        extents.append((min(lo, middle - half), max(hi, middle + half)))
    lanes = assign_lanes(extents, LANE_GAP * scale)
    lane_widths = [depth] * (max(lanes, default=-1) + 1)
    for item, lane in zip(outside, lanes, strict=True):
        if item.text:
            across = frame.split(item.size)[1]
            lane_widths[lane] = max(lane_widths[lane], depth + label_gap + across)

    columns = gutter_columns(
        max((frame.split(m.size)[1] for m in marks), default=0.0),
        lane_widths,
        max((frame.split(n.size)[1] for n in notes), default=0.0),
        start=AXIS_GAP * scale,
        gap=COLUMN_GAP * scale,
    )
    texts = _spread_column(ax, frame, marks, columns.marks.near, MARK_GAP * scale)
    texts += _spread_column(ax, frame, notes, columns.notes.near, NOTE_GAP * scale)

    placed: list[PlacedBrace] = []
    for item, lane in zip(outside, lanes, strict=True):
        lo, hi = _span(ax, frame, item.resolved.layer)
        near = columns.braces[lane].near
        base = frame.point(0, near)[0 if frame.axis == "y" else 1]
        outline = brace_outline(lo, hi, base=base, depth=depth, direction=-1, axis=frame.axis)
        placed.append(PlacedBrace(item.resolved, outline, 0.0))
        if item.text:
            anchor = frame.point((lo + hi) / 2, near + depth + label_gap)
            texts.append(
                GutterText(item.resolved, item.text, anchor, f"{item.resolved.layer.id}.label")
            )

    # Inside braces step into the plot, one lane per overlap.
    inner = assign_lanes([_span(ax, frame, b.resolved.layer) for b in inside], LANE_GAP * scale)
    inside_placed = []
    for item, lane in zip(inside, inner, strict=True):
        lo, hi = _span(ax, frame, item.resolved.layer)
        offset = INSIDE_GAP * scale + lane * (depth + LABEL_GAP * scale)
        base = frame.point(0, -offset)[0 if frame.axis == "y" else 1]
        outline = brace_outline(lo, hi, base=base, depth=depth, direction=1, axis=frame.axis)
        inside_placed.append(PlacedBrace(item.resolved, outline, (hi - lo) / 2))
    return GutterPlan(tuple(texts), tuple(placed + inside_placed), tuple(inside_placed))
