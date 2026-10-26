"""Ink boxes of glyph outlines, exact and cached per glyph.

Matplotlib's ``Path.get_extents`` solves the Bezier extrema of every segment through
``numpy.roots``, which was most of the time a label took to set. A glyph's ink depends only on the
face, the glyph and the scale, so it is computed once at the origin, from the outline commands
directly, and shifted by the glyph's position.
"""

from __future__ import annotations

from typing import Any

from glyphkit.outlines import ClosePath, CubicTo, LineTo, MoveTo, QuadraticTo

InkBox = tuple[float, float, float, float]
"""``x0, y0, x1, y1`` of the ink of some outlines."""


def glyph_ink(
    cache: dict[Any, InkBox | None],
    glyph: Any,
    commands: Any,
    scale: float,
    dx: float,
    dy: float,
) -> InkBox | None:
    """The ink box of one glyph drawn at ``(dx, dy)``, from a per-glyph cache.

    Matplotlib solves the Bezier extrema of a path segment by segment, which dominates the
    time a label takes to set. A glyph's ink depends only on the face, the glyph and the
    scale, so it is computed once at the origin and shifted by the glyph's position.
    """
    key = (glyph.face_id, glyph.glyph_id, glyph.variation_coordinates, scale)
    if key not in cache:
        cache[key] = _outline_ink(commands, scale)
    local = cache[key]
    if local is None:
        return None
    return (local[0] + dx, local[1] + dy, local[2] + dx, local[3] + dy)


def _curve_extrema(*p: float) -> list[float]:
    """The parameters in ``(0, 1)`` where a quadratic or cubic Bezier is extreme along one axis."""
    if len(p) == 3:
        denominator = p[0] - 2 * p[1] + p[2]
        return [] if denominator == 0 else [(p[0] - p[1]) / denominator]
    a = p[3] - 3 * p[2] + 3 * p[1] - p[0]
    b = 2 * (p[2] - 2 * p[1] + p[0])
    c = p[1] - p[0]
    if a == 0:
        return [] if b == 0 else [-c / b]
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return []
    root = discriminant**0.5
    return [(-b + root) / (2 * a), (-b - root) / (2 * a)]


def _bezier_at(t: float, *p: float) -> float:
    """The Bezier of control values ``p`` at ``t`` (de Casteljau)."""
    values = list(p)
    while len(values) > 1:
        values = [(1 - t) * u + t * v for u, v in zip(values, values[1:], strict=False)]
    return values[0]


def _outline_ink(commands: Any, scale: float) -> InkBox | None:
    """The exact ink box of an outline scaled by ``scale`` with its origin at the point (0, 0)."""
    xs: list[float] = []
    ys: list[float] = []
    current = start = (0.0, 0.0)
    drawn = False

    def take(*points: tuple[float, float]) -> None:
        nonlocal current, drawn
        chain = (current, *points)
        for axis, out in ((0, xs), (1, ys)):
            values = [point[axis] for point in chain]
            out.extend(values[:1] + values[-1:])
            if len(values) > 2:
                out.extend(_bezier_at(t, *values) for t in _curve_extrema(*values) if 0.0 < t < 1.0)
        current, drawn = points[-1], True

    def scaled(point: tuple[float, float]) -> tuple[float, float]:
        return (point[0] * scale, point[1] * scale)

    for command in commands:
        if isinstance(command, MoveTo):
            current = start = scaled(command.point)
        elif isinstance(command, LineTo):
            take(scaled(command.point))
        elif isinstance(command, QuadraticTo):
            take(scaled(command.control), scaled(command.point))
        elif isinstance(command, CubicTo):
            take(scaled(command.control1), scaled(command.control2), scaled(command.point))
        elif isinstance(command, ClosePath):
            take(start)
    return (min(xs), min(ys), max(xs), max(ys)) if drawn else None


def union_ink(boxes: list[InkBox]) -> InkBox:
    """The smallest box around ``boxes``."""
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )
