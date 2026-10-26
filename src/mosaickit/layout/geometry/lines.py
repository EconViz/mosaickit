"""Clipping and line construction in arbitrary Cartesian coordinates."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from mosaickit.errors import ConfigurationError
from mosaickit.layout.geometry.rect import Point, Rect, Segment

Polyline = tuple[Point, ...]

_EPSILON = 1e-12


def _ordered_rect(rect: Rect) -> tuple[float, float, float, float]:
    """Return rectangle bounds in increasing order.

    ``Rect`` is also used for measured boxes whose endpoints may arrive in either
    order.  Geometry operations therefore normalize the bounds locally instead of
    imposing a new invariant on the existing type.
    """
    return (
        min(rect.x0, rect.x1),
        min(rect.y0, rect.y1),
        max(rect.x0, rect.x1),
        max(rect.y0, rect.y1),
    )


def _finite_point(point: Point, *, name: str) -> None:
    if len(point) != 2 or not all(math.isfinite(value) for value in point):
        raise ConfigurationError(f"{name} must contain two finite coordinates")


def _points_close(first: Point, second: Point) -> bool:
    scale = max(1.0, *(abs(value) for point in (first, second) for value in point))
    return (
        abs(first[0] - second[0]) <= _EPSILON * scale
        and abs(first[1] - second[1]) <= _EPSILON * scale
    )


def clip_segment(start: Point, end: Point, rect: Rect) -> Segment | None:
    """Return the portion of a closed segment inside an axis-aligned rectangle.

    Endpoints on the boundary are retained.  A zero-length segment is returned
    unchanged when its point lies inside ``rect`` and returns ``None`` otherwise.
    Rectangle endpoints may be supplied in either order.
    """
    _finite_point(start, name="start")
    _finite_point(end, name="end")
    x_min, y_min, x_max, y_max = _ordered_rect(rect)
    ax, ay = start
    dx, dy = end[0] - ax, end[1] - ay
    lower, upper = 0.0, 1.0

    for coefficient, distance in (
        (-dx, ax - x_min),
        (dx, x_max - ax),
        (-dy, ay - y_min),
        (dy, y_max - ay),
    ):
        if coefficient == 0.0:
            if distance < 0.0:
                return None
            continue
        parameter = distance / coefficient
        if coefficient < 0.0:
            lower = max(lower, parameter)
        else:
            upper = min(upper, parameter)
        if lower > upper:
            return None

    return (
        (ax + lower * dx, ay + lower * dy),
        (ax + upper * dx, ay + upper * dy),
    )


def clip_polyline_fragments(points: Sequence[Point], rect: Rect) -> tuple[Polyline, ...]:
    """Clip a polyline to ``rect`` and return its connected visible fragments.

    A polyline can leave and later re-enter a rectangle, so the result is a tuple
    of fragments rather than one flattened path.  Each fragment has at least two
    points.  Consecutive visible segments sharing a boundary or input vertex are
    joined without duplicating that point.
    """
    if len(points) < 2:
        raise ConfigurationError("a polyline needs at least two points")
    for index, point in enumerate(points):
        _finite_point(point, name=f"points[{index}]")

    fragments: list[list[Point]] = []
    current: list[Point] = []
    for start, end in zip(points, points[1:], strict=False):
        clipped = clip_segment(start, end, rect)
        if clipped is None:
            if current:
                fragments.append(current)
                current = []
            continue
        first, last = clipped
        if current and _points_close(current[-1], first):
            if not _points_close(current[-1], last):
                current.append(last)
        else:
            if current:
                fragments.append(current)
            current = [first, last]
    if current:
        fragments.append(current)
    return tuple(tuple(fragment) for fragment in fragments)


def _chord(points: Sequence[Point]) -> tuple[Point, Point, float, float]:
    if len(points) < 2:
        raise ConfigurationError("a chord needs at least two points")
    for index, point in enumerate(points):
        _finite_point(point, name=f"points[{index}]")
    first = points[0]
    last = next((point for point in reversed(points[1:]) if not _points_close(first, point)), None)
    if last is None:
        raise ConfigurationError("a chord needs two distinct points")
    return first, last, last[0] - first[0], last[1] - first[1]


def extend_chord(
    points: Sequence[Point],
    *,
    before: float = 0.0,
    after: float | None = None,
    relative: bool = False,
) -> Segment:
    """Extend the chord through solved ``points`` before its first and after its last point.

    ``before`` and ``after`` are distances in the points' coordinate system.  With
    ``relative=True`` they are instead fractions of the distance between the two
    chord endpoints; ``0.25`` therefore preserves a quarter-span tail on that side.
    When ``after`` is omitted it equals ``before``.  Interior points do not alter the
    chord: the first point and last distinct point determine its direction.
    """
    if after is None:
        after = before
    for name, value in (("before", before), ("after", after)):
        if not math.isfinite(value) or value < 0.0:
            raise ConfigurationError(f"{name} must be non-negative and finite")

    first, last, dx, dy = _chord(points)
    length = math.hypot(dx, dy)
    before_distance = before * length if relative else before
    after_distance = after * length if relative else after
    unit_x, unit_y = dx / length, dy / length
    return (
        (first[0] - before_distance * unit_x, first[1] - before_distance * unit_y),
        (last[0] + after_distance * unit_x, last[1] + after_distance * unit_y),
    )


def _line_to_rect(origin: Point, direction: Point, rect: Rect) -> Segment | None:
    x_min, y_min, x_max, y_max = _ordered_rect(rect)
    ox, oy = origin
    dx, dy = direction
    if abs(dx) <= _EPSILON and abs(dy) <= _EPSILON:
        raise ConfigurationError("line direction must be non-zero")

    candidates: list[tuple[float, Point]] = []
    if abs(dx) > _EPSILON:
        for x in (x_min, x_max):
            parameter = (x - ox) / dx
            y = oy + parameter * dy
            if y_min - _EPSILON <= y <= y_max + _EPSILON:
                candidates.append((parameter, (x, min(max(y, y_min), y_max))))
    if abs(dy) > _EPSILON:
        for y in (y_min, y_max):
            parameter = (y - oy) / dy
            x = ox + parameter * dx
            if x_min - _EPSILON <= x <= x_max + _EPSILON:
                candidates.append((parameter, (min(max(x, x_min), x_max), y)))

    candidates.sort(key=lambda item: item[0])
    unique: list[Point] = []
    for _, point in candidates:
        if not unique or not _points_close(unique[-1], point):
            unique.append(point)
    if len(unique) < 2:
        return None
    unique.sort()
    return unique[0], unique[-1]


def chord_to_rect(points: Sequence[Point], rect: Rect) -> Segment | None:
    """Extend the infinite chord through ``points`` to the edges of ``rect``.

    Returns ``None`` when the line does not cross the rectangle.  Vertical and
    horizontal chords are supported, as are rectangles whose endpoints are reversed.
    """
    first, _, dx, dy = _chord(points)
    return _line_to_rect(first, (dx, dy), rect)


def _validate_coordinate_rect(rect: Rect, *, name: str) -> None:
    values = (rect.x0, rect.y0, rect.x1, rect.y1)
    if not all(math.isfinite(value) for value in values):
        raise ConfigurationError(f"{name} must have finite bounds")
    if rect.width <= 0.0 or rect.height <= 0.0:
        raise ConfigurationError(f"{name} must have positive width and height")


def line_through_display_slope(
    point: Point,
    slope: float,
    *,
    data_rect: Rect,
    display_rect: Rect,
) -> Segment | None:
    """Construct a viewport-wide line with a requested display-space ``slope``.

    ``point`` and the returned segment use data coordinates.  ``data_rect`` is the
    visible data viewport; ``display_rect`` gives its physical or pixel extent.
    Accounting for both rectangles makes the apparent slope independent of panel
    aspect ratio.  Positive or negative infinity requests a vertical line.
    """
    _finite_point(point, name="point")
    _validate_coordinate_rect(data_rect, name="data_rect")
    _validate_coordinate_rect(display_rect, name="display_rect")
    if math.isnan(slope):
        raise ConfigurationError("slope must not be NaN")

    if math.isinf(slope):
        direction = (0.0, 1.0)
    else:
        direction = (
            data_rect.width / display_rect.width,
            slope * data_rect.height / display_rect.height,
        )
    return _line_to_rect(point, direction, data_rect)


def line_through_display_angle(
    point: Point,
    angle_degrees: float,
    *,
    data_rect: Rect,
    display_rect: Rect,
) -> Segment | None:
    """Construct a viewport-wide line at ``angle_degrees`` in display space.

    The angle is counter-clockwise from the display x-axis.  Angles differing by
    180 degrees describe the same line.  Coordinate transformation happens before
    clipping, so vertical angles remain exactly vertical on non-square panels.
    """
    _finite_point(point, name="point")
    _validate_coordinate_rect(data_rect, name="data_rect")
    _validate_coordinate_rect(display_rect, name="display_rect")
    if not math.isfinite(angle_degrees):
        raise ConfigurationError("angle_degrees must be finite")

    radians = math.radians(angle_degrees)
    direction = (
        math.cos(radians) * data_rect.width / display_rect.width,
        math.sin(radians) * data_rect.height / display_rect.height,
    )
    return _line_to_rect(point, direction, data_rect)


def clip_polyline(
    points: Sequence[Point],
    x_range: tuple[float, float],
    y_range: tuple[float, float],
) -> Polyline:
    """Clip a polyline to ``x_range`` by ``y_range`` (Liang-Barsky) and return what is visible.

    Returns an empty tuple when nothing is visible.  A polyline that leaves and re-enters
    the rectangle has no single visible path, so it raises; use ``clip_polyline_fragments``
    for that case.  Ranges may be given in either order.
    """
    rect = Rect(x_range[0], y_range[0], x_range[1], y_range[1])
    fragments = clip_polyline_fragments(points, rect)
    if len(fragments) > 1:
        raise ConfigurationError(
            "the polyline leaves and re-enters the view; use clip_polyline_fragments"
        )
    return fragments[0] if fragments else ()


def extend_line_through(
    points: Sequence[Point],
    *,
    before: float = 0.0,
    after: float | None = None,
) -> Segment:
    """Return the chord through the first and last of ``points`` with a tail at each end.

    ``before`` and ``after`` are shares of the chord length (``after`` defaults to
    ``before``); the result is the two extended end points.
    """
    return extend_chord(points, before=before, after=after, relative=True)


def display_slope(
    data_slope: float, x_span: float, y_span: float, width: float, height: float
) -> float:
    """Return the on-screen slope of a line with ``data_slope`` on a width-by-height view."""
    _positive(x_span=x_span, y_span=y_span, width=width, height=height)
    _finite(data_slope=data_slope)
    return data_slope * (x_span / y_span) * (height / width)


def data_slope_for_display(
    display_slope: float, x_span: float, y_span: float, width: float, height: float
) -> float:
    """Return the data slope that appears with ``display_slope``; inverse of ``display_slope``."""
    _positive(x_span=x_span, y_span=y_span, width=width, height=height)
    _finite(display_slope=display_slope)
    return display_slope * (y_span / x_span) * (width / height)


def axis_span_for_display_slope(
    data_slope: float, x_span: float, display_slope: float, width: float, height: float
) -> float:
    """Return the y span at which a line of ``data_slope`` appears with ``display_slope``.

    Only magnitudes matter, so the result is always positive; ``display_slope`` must be
    non-zero and ``data_slope`` must not be zero.
    """
    _positive(x_span=x_span, width=width, height=height)
    _finite(data_slope=data_slope, display_slope=display_slope)
    if data_slope == 0.0 or display_slope == 0.0:
        raise ConfigurationError("data_slope and display_slope must be non-zero")
    return abs(data_slope) * x_span * height / (width * abs(display_slope))


@dataclass(frozen=True)
class View:
    """A rectangular window onto data: origin plus spans along each axis."""

    x_origin: float
    y_origin: float
    x_span: float
    y_span: float

    def shift(self, point: Point) -> Point:
        """Return ``point`` relative to the view origin."""
        return point[0] - self.x_origin, point[1] - self.y_origin


def centered_view(
    points: Sequence[Point],
    *,
    gap_share: float,
    display_slope: float | None = None,
    data_slope: float | None = None,
    width: float = 1.0,
    height: float = 1.0,
) -> View:
    """Return a view centred on the midpoint of the first and last of ``points``.

    The horizontal distance between the two points is ``gap_share`` of the x span.  By
    default the vertical distance is the same share of the y span.  With ``display_slope``
    the y span instead makes a line of ``data_slope`` (default: the slope of the chord)
    look that steep on a ``width`` by ``height`` view.
    """
    if len(points) < 2:
        raise ConfigurationError("a view needs at least two points")
    for index, point in enumerate(points):
        _finite_point(point, name=f"points[{index}]")
    _positive(gap_share=gap_share, width=width, height=height)
    if gap_share > 1.0:
        raise ConfigurationError("gap_share must not exceed 1")
    (x0, y0), (x1, y1) = points[0], points[-1]
    gap = abs(x1 - x0)
    if gap <= _EPSILON:
        raise ConfigurationError("the points need distinct horizontal values")
    x_span = gap / gap_share
    if display_slope is None:
        if abs(y1 - y0) <= _EPSILON:
            raise ConfigurationError("the points need distinct vertical values")
        y_span = abs(y1 - y0) / gap_share
    else:
        slope = (y1 - y0) / (x1 - x0) if data_slope is None else data_slope
        y_span = axis_span_for_display_slope(slope, x_span, display_slope, width, height)
    return View(
        x_origin=(x0 + x1) / 2 - x_span / 2,
        y_origin=(y0 + y1) / 2 - y_span / 2,
        x_span=x_span,
        y_span=y_span,
    )


def _finite(**values: float) -> None:
    for name, value in values.items():
        if not math.isfinite(value):
            raise ConfigurationError(f"{name} must be finite")


def _positive(**values: float) -> None:
    for name, value in values.items():
        if not math.isfinite(value) or value <= 0.0:
            raise ConfigurationError(f"{name} must be positive and finite")


__all__ = [
    "Polyline",
    "View",
    "axis_span_for_display_slope",
    "centered_view",
    "chord_to_rect",
    "clip_polyline",
    "clip_polyline_fragments",
    "clip_segment",
    "data_slope_for_display",
    "display_slope",
    "extend_chord",
    "extend_line_through",
    "line_through_display_angle",
    "line_through_display_slope",
]
