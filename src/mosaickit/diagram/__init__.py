"""A small declarative builder for theory diagrams: axes, curves, named points, guides."""

from mosaickit.diagram._names import DEFAULT_NAME_ORDER, RISING_NAME_ORDER
from mosaickit.diagram.builder import (
    Diagram,
    PointLink,
    indexed,
    is_symbol,
    link_points,
    primed,
    stack,
)

__all__ = [
    "DEFAULT_NAME_ORDER",
    "RISING_NAME_ORDER",
    "Diagram",
    "PointLink",
    "indexed",
    "is_symbol",
    "link_points",
    "primed",
    "stack",
]
