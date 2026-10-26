"""The :class:`Diagram` builder: its layers, curve names, canvas spec and canvas."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from mosaickit.canvas import Canvas
from mosaickit.canvas_spec import CanvasSpec
from mosaickit.diagram._names import RISING_NAME_ORDER, SIDES, place_name
from mosaickit.diagram.builder.constants import (
    DOT_RADIUS,
    NAME_CLEARANCE,
    ORIGIN_OFFSET,
    OVERHANG,
    TITLE_GAP,
    NudgeFor,
    Point,
)
from mosaickit.diagram.builder.primitives import _Primitives
from mosaickit.diagram.builder.symbols import is_symbol
from mosaickit.layout import Obstacles, Rect
from mosaickit.scene import (
    ArrowLayer,
    Layer,
    MarkerLayer,
    PathLayer,
    PointLabelLayer,
    TextLayer,
)
from mosaickit.styles import ArrowPlacement, ArrowStyle, Stroke
from mosaickit.styles.nudge import Nudge


class Diagram(_Primitives):
    """One panel: arrowed axes from the origin, then curves, named points, guides and arrows.

    Every coordinate is in data units. With a ``view`` (see :func:`mosaickit.layout.centered_view`)
    the axes show the window ``[x_origin, x_origin + x_span]`` and so on: coordinates are given
    in data and shifted by the builder, so panels may use shifted origins. Methods return
    ``self``; :meth:`canvas` builds a :class:`~mosaickit.Canvas` and places curve names clear
    of every line, point and name.

    ``theme``/``config`` go to the canvas. ``nudge`` is called with each label layer and may
    return a :class:`~mosaickit.Nudge` that is added to the layer's own, so a downstream
    package can drive label offsets from its settings. ``id_prefix`` is put before every layer id.
    """

    # -- build ---------------------------------------------------------------------------

    def _axes(self) -> list[Layer]:
        arrow = Stroke(arrow=ArrowStyle.TRIANGLE)
        role = self.axes_role
        layers: list[Layer] = [
            PathLayer(
                ((0.0, 0.0), (self.x_max, 0.0)),
                id=self._id("axes.x"),
                role=role,
                stroke=arrow,
                arrow_placement=ArrowPlacement.END,
                clip=False,
            ),
            PathLayer(
                ((0.0, 0.0), (0.0, self.y_max)),
                id=self._id("axes.y"),
                role=role,
                stroke=arrow,
                arrow_placement=ArrowPlacement.END,
                clip=False,
            ),
        ]
        if self.y_label:
            layers.append(
                TextLayer(
                    (0.0, self.y_max),
                    self.y_label,
                    id=self._id("axes.y.label"),
                    role=role,
                    anchor="bottom",
                    offset=(0, TITLE_GAP),
                    math=is_symbol(self.y_label),
                )
            )
        if self.x_label:
            symbol = is_symbol(self.x_label)
            layers.append(
                TextLayer(
                    (self.x_max, 0.0),
                    self.x_label,
                    id=self._id("axes.x.label"),
                    role=role,
                    anchor="left" if symbol else "top-right",
                    offset=(TITLE_GAP, 0) if symbol else (0, -TITLE_GAP),
                    math=symbol,
                )
            )
        if self.origin_label:
            layers.append(
                TextLayer(
                    (0.0, 0.0),
                    self.origin_label,
                    id=self._id("axes.origin.label"),
                    role=role,
                    anchor="right",
                    offset=ORIGIN_OFFSET,
                )
            )
        return layers

    def _name_layers(self, others: Sequence[Layer]) -> list[Layer]:
        """The curve names, each at the first free side of its curve's end."""
        if not self._curves:
            return []
        sx = self.width * 72.0 * self.plot_share / self.x_max
        sy = self.height * 72.0 * self.plot_share / self.y_max
        segments: list[tuple[Point, Point]] = []
        rects: list[Rect] = []
        for layer in [*others, *(c.layer for c in self._curves)]:
            if isinstance(layer, PathLayer):
                pts = [(x * sx, y * sy) for x, y in layer.path]
                segments.extend(zip(pts, pts[1:], strict=False))
            elif isinstance(layer, ArrowLayer):
                a = (layer.start[0] * sx, layer.start[1] * sy)
                b = (layer.end[0] * sx, layer.end[1] * sy)
                segments.append((a, b))
            elif isinstance(layer, MarkerLayer):
                rects.extend(
                    Rect.centered((x * sx, y * sy), 2 * DOT_RADIUS, 2 * DOT_RADIUS)
                    for x, y in layer.points
                )
        bounds = Rect(0.0, 0.0, self.x_max * sx * OVERHANG, self.y_max * sy)
        obstacles = Obstacles(tuple(segments), tuple(rects))
        names: list[Layer] = []
        for curve in self._curves:
            path = curve.layer.path
            end = max(path, key=lambda p: (p[0], p[1]))
            anchor = (end[0] * sx, end[1] * sy)
            rising = path[-1][1] > path[0][1]
            if curve.side is not None:
                order: Sequence[str] = (curve.side,)
            elif self.rising_names_upper_right and rising:
                order = RISING_NAME_ORDER
            else:
                order = self.name_order
            size = self.text_size(curve.label, self.font_size)
            placed = place_name(
                anchor,
                size,
                obstacles,
                bounds,
                order,
                gap=self.name_gap,
                clearance=NAME_CLEARANCE,
                diagonal=self.name_diagonal,
            )
            obstacles = Obstacles(obstacles.segments, (*obstacles.rects, placed.box))
            names.append(
                TextLayer(
                    end,
                    curve.label,
                    id=f"{curve.layer.id}.label",
                    role=curve.layer.role,
                    anchor=SIDES[placed.side][2],
                    offset=placed.offset,
                    z_index=curve.z_index,
                )
            )
        return names

    def layers(self) -> list[Layer]:
        """Every layer of the panel, with curve names placed and nudges applied."""
        base = [*self._axes(), *self._layers]
        layers = [*base, *self._name_layers(base)]
        if self.nudge is None:
            return layers
        return [_nudged(layer, self.nudge) for layer in layers]

    def spec(self) -> CanvasSpec:
        """The canvas spec: axes from the origin; axis titles are drawn as layers."""
        return CanvasSpec(
            x_range=(0.0, self.x_max),
            y_range=(0.0, self.y_max),
            width=self.width,
            height=self.height,
            x_label="",
            y_label="",
            title=self.title,
        )

    def canvas(self, **canvas_options: Any) -> Canvas:
        """The finished :class:`~mosaickit.Canvas` (``canvas_options`` go to its constructor)."""
        options: dict[str, Any] = {"theme": self.theme, "config": self.config}
        options.update(canvas_options)
        return Canvas(self.spec(), **options).extend(self.layers())


def _nudged(layer: Layer, nudge_for: NudgeFor) -> Layer:
    if not isinstance(layer, (TextLayer, PointLabelLayer)):
        return layer
    extra = nudge_for(layer)
    if extra is None:
        return layer
    current = layer.nudge
    if current is not None:
        extra = Nudge(current.dx + extra.dx, current.dy + extra.dy)
    return replace(layer, nudge=extra)
