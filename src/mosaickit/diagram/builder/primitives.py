"""The drawing primitives of a diagram: curves, points, guides and arrows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from mosaickit.diagram._names import SIDES
from mosaickit.diagram.builder.constants import Point, Ref
from mosaickit.diagram.builder.panel import _Curve, _Panel
from mosaickit.errors import ConfigurationError
from mosaickit.layout import extend_line_through
from mosaickit.scene import (
    ArrowLayer,
    AxisMarkLayer,
    MarkerLayer,
    PathLayer,
    PointLabelLayer,
    TextLayer,
)
from mosaickit.styles.nudge import Nudge

_D = TypeVar("_D", bound="_Primitives")
"""The concrete diagram class, so that chained calls keep returning it."""


def _sign(value: float) -> int:
    return (value > 0) - (value < 0)


_OFFSET_ANCHOR = {(sx, sy): anchor for sx, sy, anchor in [*SIDES.values(), (0, 0, "center")]}


class _Primitives(_Panel):
    """The methods of a :class:`~mosaickit.diagram.Diagram` that add layers to it."""

    # -- primitives ----------------------------------------------------------------------

    def curve(
        self: _D,
        name: str,
        points: Sequence[Point],
        *,
        role: str = "curve",
        label: str | None = None,
        side: str | None = None,
        floor: float = 0.0,
        z_index: int = 2,
        trim: bool = True,
    ) -> _D:
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
        self: _D,
        name: str,
        points: Sequence[Point],
        *,
        tail: float = 0.1,
        role: str = "curve",
        label: str | None = None,
        side: str | None = None,
        floor: float = 0.0,
        z_index: int = 2,
    ) -> _D:
        """The chord through the first and last of ``points`` (data), ``tail`` of its length
        longer at each end, clipped to the plot. Use it for short-tailed solved lines."""
        chord = extend_line_through(sorted(points), before=tail)
        return self.curve(
            name, chord, role=role, label=label, side=side, floor=floor, z_index=z_index
        )

    def tail_label(
        self: _D,
        name: str,
        curve: str,
        text: str,
        *,
        offset: Point,
        role: str | None = None,
        anchor: str | None = None,
        z_index: int = 7,
    ) -> _D:
        """``text`` at a fixed ``offset`` (points) from the end of the curve ``curve``.

        Unlike a curve name it is not searched for a free spot. The end is the curve's point
        farthest right (then highest). Unless ``anchor`` is given, the text sits on the side the
        offset points to: right of the end for ``(8, 0)``, above it for ``(0, 8)``. ``role``
        defaults to the curve's.
        """
        layer = next(
            (c for c in self._layers if isinstance(c, PathLayer) and c.id == self._id(curve)), None
        )
        if layer is None:
            raise ConfigurationError(f"unknown curve {curve!r}; declare it with curve() first")
        dx, dy = offset
        if anchor is None:
            anchor = _OFFSET_ANCHOR[(_sign(dx), _sign(dy))]
        end = max(layer.path, key=lambda p: (p[0], p[1]))
        self._layers.append(
            TextLayer(
                end,
                text,
                id=self._id(name),
                role=role or layer.role,
                anchor=anchor,
                offset=(float(dx), float(dy)),
                z_index=z_index,
            )
        )
        return self

    def point(
        self: _D,
        name: str,
        at: Point,
        label: str | None = None,
        *,
        role: str = "point",
        nudge: Nudge | None = None,
        z_index: int = 6,
    ) -> _D:
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

    def axis_mark(self: _D, axis: str, value: float, label: str, *, name: str) -> _D:
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
        self: _D, start: Ref, end: Ref, *, name: str, role: str = "guide", z_index: int = 1
    ) -> _D:
        """A dashed guide (the ``guide`` role) between two points."""
        path = (self.at(start), self.at(end))
        self._layers.append(PathLayer(path, id=self._id(name), role=role, z_index=z_index))
        return self

    def drop(
        self: _D,
        ref: Ref,
        *,
        x: str | None = None,
        y: str | None = None,
        name: str | None = None,
        role: str = "guide",
    ) -> _D:
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
        self: _D,
        name: str,
        start: Ref,
        end: Ref,
        label: str | None = None,
        *,
        role: str = "annotation",
        label_role: str | None = None,
        z_index: int = 5,
    ) -> _D:
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
