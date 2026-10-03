"""Candidate label rects around an origin, shared by every placement search."""

import math

from mosaickit.layout.geometry import Point, Rect

_SIDE = 0.38  # |cos| above this anchors the rect by its near side, otherwise by its middle


def direction(k: int, count: int) -> Point:
    """The ``k``-th of ``count`` unit directions, counter-clockwise from +x."""
    angle = 2 * math.pi * k / count
    return (math.cos(angle), math.sin(angle))


def anchored_rect(
    origin: Point, direction: Point, distance: float, size: tuple[float, float]
) -> Rect:
    """A ``size`` rect ``distance`` from ``origin`` along ``direction``, anchored by
    the side (or corner) nearest the origin so it extends away from it."""
    dx, dy = direction
    cx, cy = origin[0] + dx * distance, origin[1] + dy * distance
    width, height = size
    x0 = cx if dx > _SIDE else cx - width if dx < -_SIDE else cx - width / 2
    y0 = cy if dy > _SIDE else cy - height if dy < -_SIDE else cy - height / 2
    return Rect(x0, y0, x0 + width, y0 + height)
