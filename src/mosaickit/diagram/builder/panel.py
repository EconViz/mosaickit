"""The state of one panel: view, options, declared points and coordinate conversion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from mosaickit.configuration import Config
from mosaickit.diagram._names import DEFAULT_NAME_ORDER, SIDES, TextSize
from mosaickit.diagram._text_size import estimate_text_size
from mosaickit.diagram.builder.constants import (
    HEADROOM,
    NAME_CHARACTER_WIDTH,
    NAME_DIAGONAL,
    NAME_FONT_SIZE,
    NAME_GAP,
    NAME_LINE_HEIGHT,
    PLOT_SHARE,
    NudgeFor,
    Point,
    Ref,
)
from mosaickit.errors import ConfigurationError
from mosaickit.layout import View, clip_polyline
from mosaickit.scene import Layer, PathLayer
from mosaickit.themes import Theme


@dataclass(frozen=True, slots=True)
class _Curve:
    layer: PathLayer
    label: str
    side: str | None
    z_index: int


def _default_text_size(label: str, font_size: float) -> Point:
    return estimate_text_size(
        label, font_size, char_width=NAME_CHARACTER_WIDTH, line_height=NAME_LINE_HEIGHT
    )


class _Panel:
    """The state and coordinates of a :class:`~mosaickit.diagram.Diagram`."""

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
        name_gap: float = NAME_GAP,
        name_diagonal: float = NAME_DIAGONAL,
        text_size: TextSize | None = None,
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
        self.name_gap, self.name_diagonal = name_gap, name_diagonal
        self.text_size: TextSize = text_size or _default_text_size
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
