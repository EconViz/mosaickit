"""One call for a figure package: place its labels against a snapshot of the whole scene.

``place_scene_labels`` turns the layers of a canvas snapshot into one obstacle scene (curves,
arrows, markers, texts that stay where they are, extra fixed boxes such as axis titles and
tick labels), places the labels you name together with
:func:`~mosaickit.layout.labels.place_labels`, and returns replacement layers: each name
as a :class:`~mosaickit.scene.TextLayer` with its ``anchor`` and ``offset`` set (the
position stays the label's own anchor), and a leader :class:`~mosaickit.scene.PathLayer` where a
label sits further out than ``LabelOptions.leader_after``. Sizes come from ``measure``;
the font size is never changed.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal

from mosaickit.layout import Rect
from mosaickit.layout.labels import (
    Label,
    LabelOptions,
    Obstacle,
    PlacementResult,
    place_labels,
)
from mosaickit.layout.labels.candidates import COMPASS_UNITS
from mosaickit.scene import ArrowLayer, Layer, MarkerLayer, PathLayer, TextLayer
from mosaickit.scene.text import TEXT_ANCHORS
from mosaickit.styles import Stroke

Point = tuple[float, float]
Measure = Callable[[str], tuple[float, float]]
"""Size ``(width, height)`` in points of a text as it is drawn."""
CurveEnd = Literal["rightmost", "last", "first", "top"]


@dataclass(frozen=True, slots=True)
class SceneLabelOptions:
    """Scene-level parameters of :func:`place_scene_labels`."""

    marker_radius: float = 4.0
    """Radius in points kept clear around a marker."""
    leader_role: str = "annotation.leader"
    """Role of the leader layers, so a theme styles them."""
    leader_stroke: Stroke | None = None
    """Explicit stroke of the leaders; ``None`` leaves it to the theme role."""
    tick_sides: Sequence[str] = ("below", "above")
    """Sides of a tick label, preferred first (``("left", "right")`` for a vertical axis)."""
    placement: LabelOptions = LabelOptions()


def curve_end(path: Sequence[Point], end: CurveEnd = "rightmost") -> Point:
    """The point of ``path`` a curve name belongs to, by a named policy."""
    if end == "last":
        return tuple(path[-1])  # type: ignore[return-value]
    if end == "first":
        return tuple(path[0])  # type: ignore[return-value]
    if end == "top":
        return max(path, key=lambda p: (p[1], p[0]))
    return max(path, key=lambda p: (p[0], p[1]))


def _numeric(point: object) -> bool:
    return (
        isinstance(point, tuple)
        and len(point) == 2
        and all(isinstance(v, (int, float)) and math.isfinite(v) for v in point)
    )


def _text_box(layer: TextLayer, scale: Point, measure: Measure) -> Rect | None:
    if not _numeric(layer.position) or not isinstance(layer.text, str):
        return None
    ox, oy = layer.total_offset
    px = layer.position[0] * scale[0] + ox
    py = layer.position[1] * scale[1] + oy
    width, height = measure(layer.text)
    horizontal, vertical = TEXT_ANCHORS[layer.anchor]
    x0 = px if horizontal == "left" else px - width if horizontal == "right" else px - width / 2
    y0 = py if vertical == "bottom" else py - height if vertical == "top" else py - height / 2
    return Rect(x0, y0, x0 + width, y0 + height)


def scene_obstacles(
    layers: Sequence[Layer],
    scale: Point,
    measure: Measure,
    options: SceneLabelOptions,
    *,
    skip: frozenset[str] = frozenset(),
    owners: Mapping[str, str] | None = None,
) -> list[Obstacle]:
    """Lines, arrows, markers and texts of ``layers`` as obstacles in points.

    A layer in ``skip`` is left out (the labels being placed). ``owners`` maps a layer id to
    the id of the label that owns it (its own curve gets the label's ``own_clearance``).
    """
    owned = owners or {}
    found: list[Obstacle] = []
    for layer in layers:
        if layer.id in skip or not layer.visible:
            continue
        owner = owned.get(layer.id)
        if isinstance(layer, PathLayer) and all(_numeric(p) for p in layer.path):
            pts = [(x * scale[0], y * scale[1]) for x, y in layer.path]
            found.append(Obstacle.polyline(pts, owner))
        elif isinstance(layer, ArrowLayer) and _numeric(layer.start) and _numeric(layer.end):
            a = (layer.start[0] * scale[0], layer.start[1] * scale[1])
            b = (layer.end[0] * scale[0], layer.end[1] * scale[1])
            found.append(Obstacle.polyline([a, b], owner))
        elif isinstance(layer, MarkerLayer):
            found.extend(
                Obstacle.dot((x * scale[0], y * scale[1]), options.marker_radius, owner)
                for x, y in layer.points
                if _numeric((x, y))
            )
        elif isinstance(layer, TextLayer):
            box = _text_box(layer, scale, measure)
            if box is not None:
                found.append(Obstacle.rect(box, owner))
    return found


def place_scene_labels(
    layers: Sequence[Layer],
    names: Sequence[TextLayer],
    bounds: Rect,
    scale: Point,
    measure: Measure,
    options: SceneLabelOptions | None = None,
    *,
    ticks: Sequence[TextLayer] = (),
    fixed: Sequence[Obstacle] = (),
    sides: Mapping[str, Sequence[str]] | None = None,
    owners: Mapping[str, str] | None = None,
) -> tuple[list[Layer], PlacementResult]:
    """Place ``names`` (and ``ticks``) against ``layers``, ``fixed`` boxes and each other.

    ``layers`` are the figure's layers (names and ticks may be among them: they are skipped
    as obstacles). ``bounds`` is the drawing area in points and ``scale`` the points per data
    unit; ``measure`` gives each text's real or estimated size. Each name's anchor is its own
    ``position``. ``sides`` gives a name's preferred side order by layer id, ``owners`` maps a
    name's layer id to the id of the curve it belongs to (that curve gets ``own_clearance``).
    Returns the replacement layers (swap them for the originals by id) and the structured
    result with its warnings.
    """
    o = options or SceneLabelOptions()
    owner_ids = dict(owners or {})
    texts = [*names, *ticks]
    skip = frozenset(layer.id for layer in texts)
    curves = {curve: curve for curve in owner_ids.values()}
    obstacles = scene_obstacles(layers, scale, measure, o, skip=skip, owners=curves)
    obstacles.extend(fixed)
    tick_ids = {layer.id for layer in ticks}
    labels: list[Label] = []
    for layer in texts:
        if not _numeric(layer.position) or not isinstance(layer.text, str):
            continue
        anchor = (layer.position[0] * scale[0], layer.position[1] * scale[1])
        is_tick = layer.id in tick_ids
        preferred = (sides or {}).get(layer.id, o.tick_sides if is_tick else tuple(COMPASS_UNITS))
        labels.append(
            Label(
                layer.id,
                anchor,
                measure(layer.text),
                preferred,
                "stack" if is_tick else "ring",
                owner_ids.get(layer.id),
            )
        )
    result = place_labels(labels, obstacles, bounds, o.placement)
    by_id = {layer.id: layer for layer in texts}
    out: list[Layer] = []
    for placed in result.placements:
        layer = by_id[placed.label_id]
        out.append(replace(layer, anchor=placed.text_anchor, offset=placed.offset))
        if placed.leader is not None:
            a, b = placed.leader
            inverse = (1 / scale[0], 1 / scale[1])
            out.append(
                PathLayer(
                    [
                        (a[0] * inverse[0], a[1] * inverse[1]),
                        (b[0] * inverse[0], b[1] * inverse[1]),
                    ],
                    stroke=o.leader_stroke,
                    id=f"{placed.label_id}.leader",
                    role=o.leader_role,
                    z_index=layer.z_index,
                )
            )
    return out, result
