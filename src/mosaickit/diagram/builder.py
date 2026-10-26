"""A declarative builder for textbook-style theory diagrams (axes, curves, points, guides)."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from mosaickit.canvas import Canvas, CanvasGrid, GridLink, GridSpacing
from mosaickit.canvas_spec import CanvasSpec
from mosaickit.config import Config
from mosaickit.diagram._names import (
    DEFAULT_NAME_ORDER,
    RISING_NAME_ORDER,
    SIDES,
    place_name,
    text_size,
)
from mosaickit.errors import ConfigurationError
from mosaickit.layout import Obstacles, Rect, View, clip_polyline, extend_line_through
from mosaickit.scene import (
    ArrowLayer,
    AxisMarkLayer,
    Layer,
    MarkerLayer,
    PathLayer,
    PointLabelLayer,
    TextLayer,
)
from mosaickit.styles import ArrowPlacement, ArrowStyle, Stroke
from mosaickit.styles.nudge import Nudge
from mosaickit.themes import Theme

Point = tuple[float, float]
Ref = str | Point
"""A point of a diagram: the name of a declared point, or ``(x, y)`` in data coordinates."""
NudgeFor = Callable[[Layer], Nudge | None]
"""Maps a label layer to the nudge (points) a configuration wants for it, or ``None``."""

TITLE_GAP = 6.0
"""Gap in points between an arrow tip and its axis title."""
HEADROOM = 0.92
"""Share of an axis a curve may reach, leaving room for its name and the axis arrow."""
PLOT_SHARE = 0.78
"""Share of a canvas side taken by the axes; the rest is margin for axis marks and titles."""
NAME_GAP = 5.0
"""Gap in points between a curve's end and its name."""
NAME_CLEARANCE = 3.5
"""Free space in points kept between a curve name and any line or other name."""
NAME_CHARACTER_WIDTH = 0.8
"""Average character width in em assumed when placing names (a margin over the real one)."""
NAME_LINE_HEIGHT = 1.25
"""Height of a line of name text in em."""
NAME_FONT_SIZE = 12.0
"""Font size in points assumed when placing names."""
DOT_RADIUS = 4.0
"""Radius in points kept clear around marked points."""
OVERHANG = 1.12
"""How far right of the axis end (as a share of the plot width) a name may reach."""
ORIGIN_OFFSET = (-7.0, -7.0)
"""Offset in points of the origin label from the corner."""


def is_symbol(label: str) -> bool:
    """Single letters and ``$...$`` titles are set as math; words stay upright."""
    wrapped = len(label) > 1 and label.startswith("$") and label.endswith("$")
    return wrapped or (len(label) == 1 and label.isalpha())


def indexed(label: str, index: int) -> str:
    """``label`` with a subscript: ``$Y$`` -> ``$Y_1$``, ``Y`` -> ``Y_1``."""
    if label.startswith("$") and label.endswith("$"):
        return f"{label[:-1]}_{index}$"
    return f"{label}_{index}"


def primed(label: str, primes: int = 1) -> str:
    """``label`` with ``primes`` primes after its last symbol: ``$A$`` -> ``$A'$``."""
    if not primes:
        return label
    mark = "'" * primes
    return f"{label[:-1]}{mark}$" if label.startswith("$") and label.endswith("$") else label + mark


class Diagram:
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

    def __init__(
        self,
        x_max: float | None = None,
        y_max: float | None = None,
        *,
        view: View | None = None,
        x_label: str | None = None,
        y_label: str | None = None,
        origin_label: str | None = None,
        title: str | None = None,
        width: float = 6.0,
        height: float = 6.0,
        theme: Theme | None = None,
        config: Config | None = None,
        nudge: NudgeFor | None = None,
        id_prefix: str = "",
        headroom: float = HEADROOM,
        axes_role: str = "axes",
        rising_names_upper_right: bool = False,
        name_order: Sequence[str] = DEFAULT_NAME_ORDER,
        plot_share: float = PLOT_SHARE,
        font_size: float = NAME_FONT_SIZE,
    ) -> None:
        if view is not None:
            if x_max is not None or y_max is not None:
                raise ConfigurationError("give either x_max/y_max or a view, not both")
            x_max, y_max = view.x_span, view.y_span
            self.view = view
        else:
            self.view = View(0.0, 0.0, x_max or 0.0, y_max or 0.0)
        if x_max is None or y_max is None or not (x_max > 0 and y_max > 0):
            raise ConfigurationError("axis lengths must be positive")
        if not 0 < headroom <= 1 or not 0 < plot_share <= 1:
            raise ConfigurationError("headroom and plot_share must be in (0, 1]")
        for side in name_order:
            if side not in SIDES:
                raise ConfigurationError(f"unknown name side {side!r}")
        self.x_max, self.y_max = float(x_max), float(y_max)
        self.x_label, self.y_label, self.origin_label = x_label, y_label, origin_label
        self.title, self.width, self.height = title, width, height
        self.theme, self.config, self.nudge = theme, config, nudge
        self.id_prefix, self.headroom, self.axes_role = id_prefix, headroom, axes_role
        self.rising_names_upper_right = rising_names_upper_right
        self.name_order = tuple(name_order)
        self.plot_share, self.font_size = plot_share, font_size
        self._points: dict[str, Point] = {}
        self._layers: list[Layer] = []
        self._curves: list[_Curve] = []

    # -- coordinates ---------------------------------------------------------------------

    def shift(self, point: Point) -> Point:
        """``point`` (data) in the panel's own coordinates, after the view's shift."""
        return self.view.shift(point)

    def resolve(self, ref: Ref) -> Point:
        """Data coordinates of a point reference."""
        if isinstance(ref, str):
            if ref not in self._points:
                raise ConfigurationError(f"unknown point {ref!r}; declare it with point() first")
            return self._points[ref]
        return (float(ref[0]), float(ref[1]))

    def at(self, ref: Ref) -> Point:
        """Panel coordinates of a point reference: the argument of a :class:`GridLink`."""
        return self.shift(self.resolve(ref))

    @property
    def points(self) -> Mapping[str, Point]:
        """The declared points, in data coordinates."""
        return dict(self._points)

    def _id(self, name: str) -> str:
        return f"{self.id_prefix}{name}"

    def _trim(self, points: Sequence[Point], floor: float = 0.0) -> list[Point]:
        shifted = [self.shift(p) for p in points]
        kept = clip_polyline(
            shifted,
            (0.0, self.headroom * self.x_max),
            (floor * self.y_max, self.headroom * self.y_max),
        )
        if len(kept) < 2:
            raise ConfigurationError("the curve does not enter the plot")
        return list(kept)

    # -- primitives ----------------------------------------------------------------------

    def curve(
        self,
        name: str,
        points: Sequence[Point],
        *,
        role: str = "curve",
        label: str | None = None,
        side: str | None = None,
        floor: float = 0.0,
        z_index: int = 2,
        trim: bool = True,
    ) -> Diagram:
        """A curve through ``points`` (data) with an optional direct ``label`` at its end.

        The label goes at the first free side of ``name_order`` (or of the rising order, see
        ``rising_names_upper_right``) unless ``side`` fixes it. The path is clipped to the
        headroom of the plot, and below ``floor`` (share of the y axis) when ``trim``.
        """
        if len(points) < 2:
            raise ConfigurationError("a curve needs at least two points")
        if side is not None and side not in SIDES:
            raise ConfigurationError(f"unknown name side {side!r}")
        path = self._trim(points, floor) if trim else [self.shift(p) for p in points]
        layer = PathLayer(tuple(path), id=self._id(name), role=role, z_index=z_index)
        self._layers.append(layer)
        if label:
            self._curves.append(_Curve(layer, label, side, z_index + 5))
        return self

    def line(
        self,
        name: str,
        points: Sequence[Point],
        *,
        tail: float = 0.1,
        role: str = "curve",
        label: str | None = None,
        side: str | None = None,
        floor: float = 0.0,
        z_index: int = 2,
    ) -> Diagram:
        """The chord through the first and last of ``points`` (data), ``tail`` of its length
        longer at each end, clipped to the plot. Use it for short-tailed solved lines."""
        chord = extend_line_through(sorted(points), before=tail)
        return self.curve(
            name, chord, role=role, label=label, side=side, floor=floor, z_index=z_index
        )

    def point(
        self,
        name: str,
        at: Point,
        label: str | None = None,
        *,
        role: str = "point",
        nudge: Nudge | None = None,
        z_index: int = 6,
    ) -> Diagram:
        """A named marked point at ``at`` (data). ``label`` is placed beside it by the
        renderer's point-label search; ``nudge`` is its fixed offset in points."""
        self._points[name] = (float(at[0]), float(at[1]))
        shifted = self.shift(at)
        self._layers.append(MarkerLayer((shifted,), id=self._id(name), role=role, z_index=z_index))
        if label:
            self._layers.append(
                PointLabelLayer(
                    shifted,
                    label,
                    id=self._id(f"{name}.label"),
                    role=role,
                    nudge=nudge,
                    z_index=z_index + 1,
                )
            )
        return self

    def axis_mark(self, axis: str, value: float, label: str, *, name: str) -> Diagram:
        """A symbol at ``value`` (data) on ``axis`` (``"x"`` or ``"y"``); ``$..$`` is math."""
        if axis not in ("x", "y"):
            raise ConfigurationError("axis must be 'x' or 'y'")
        origin = self.view.x_origin if axis == "x" else self.view.y_origin
        math = label.startswith("$") and label.endswith("$")
        self._layers.append(
            AxisMarkLayer(
                axis,
                value - origin,
                label.strip("$") if math else label,
                math=math,
                id=self._id(name),
                role=self.axes_role,
            )
        )
        return self

    def guide(
        self, start: Ref, end: Ref, *, name: str, role: str = "guide", z_index: int = 1
    ) -> Diagram:
        """A dashed guide (the ``guide`` role) between two points."""
        path = (self.at(start), self.at(end))
        self._layers.append(PathLayer(path, id=self._id(name), role=role, z_index=z_index))
        return self

    def drop(
        self,
        ref: Ref,
        *,
        x: str | None = None,
        y: str | None = None,
        name: str | None = None,
        role: str = "guide",
    ) -> Diagram:
        """Guides from a point to the x axis and/or y axis, each ending in an axis mark
        whose symbol is ``x`` / ``y`` (nothing is drawn for an axis whose label is ``None``)."""
        if name is None:
            if not isinstance(ref, str):
                raise ConfigurationError("drop() of a coordinate needs a name")
            name = ref
        px, py = self.resolve(ref)
        if x is not None:
            self.guide((px, self.view.y_origin), (px, py), name=f"{name}.x.guide", role=role)
            self.axis_mark("x", px, x, name=f"{name}.x.mark")
        if y is not None:
            self.guide((self.view.x_origin, py), (px, py), name=f"{name}.y.guide", role=role)
            self.axis_mark("y", py, y, name=f"{name}.y.mark")
        return self

    def arrow(
        self,
        name: str,
        start: Ref,
        end: Ref,
        label: str | None = None,
        *,
        role: str = "annotation",
        label_role: str | None = None,
        z_index: int = 5,
    ) -> Diagram:
        """A straight movement/shift arrow from ``start`` to ``end``; ``label`` sits beside
        its middle (above a horizontal arrow, right of any other)."""
        a, b = self.at(start), self.at(end)
        self._layers.append(ArrowLayer(a, b, id=self._id(name), role=role, z_index=z_index))
        if label:
            middle = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            horizontal = abs(b[0] - a[0]) >= abs(b[1] - a[1])
            self._layers.append(
                TextLayer(
                    middle,
                    label,
                    id=self._id(f"{name}.label"),
                    role=label_role or role,
                    anchor="bottom" if horizontal else "left",
                    offset=(0, 4) if horizontal else (4, 0),
                    z_index=z_index + 2,
                )
            )
        return self

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
            size = text_size(curve.label, self.font_size, NAME_CHARACTER_WIDTH, NAME_LINE_HEIGHT)
            placed = place_name(
                anchor, size, obstacles, bounds, order, gap=NAME_GAP, clearance=NAME_CLEARANCE
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


@dataclass(frozen=True, slots=True)
class _Curve:
    layer: PathLayer
    label: str
    side: str | None
    z_index: int


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


@dataclass(frozen=True, slots=True)
class PointLink:
    """A link between named points of two panels of a :func:`stack`."""

    start_panel: int
    start: str
    end_panel: int
    end: str
    role: str = "link"
    stroke: Stroke | None = None


def link_points(
    upper: int,
    lower: int,
    names: Iterable[str],
    *,
    role: str = "link",
    stroke: Stroke | None = None,
) -> list[PointLink]:
    """One :class:`PointLink` per name, joining the point of that name in panel ``upper`` to
    the same-named point in panel ``lower`` (panels numbered in stacking order)."""
    return [PointLink(upper, n, lower, n, role=role, stroke=stroke) for n in names]


def stack(
    panels: Sequence[Diagram],
    links: Iterable[PointLink] = (),
    *,
    cols: int = 1,
    spacing: GridSpacing | None = None,
) -> CanvasGrid:
    """Panels in a :class:`~mosaickit.CanvasGrid` (one column by default, row by row), with
    each :class:`PointLink` resolved to a :class:`~mosaickit.GridLink` between their points."""
    if not panels:
        raise ConfigurationError("stack() needs at least one panel")
    resolved = []
    for link in links:
        for index in (link.start_panel, link.end_panel):
            if not 0 <= index < len(panels):
                raise ConfigurationError(f"link panel {index} is not one of {len(panels)} panels")
        resolved.append(
            GridLink(
                link.start_panel,
                panels[link.start_panel].at(link.start),
                link.end_panel,
                panels[link.end_panel].at(link.end),
                role=link.role,
                stroke=link.stroke,
            )
        )
    return CanvasGrid(
        [panel.canvas() for panel in panels], cols=cols, links=resolved, spacing=spacing
    )
