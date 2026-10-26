"""A declarative builder for textbook-style theory diagrams (axes, curves, points, guides)."""

from __future__ import annotations

from mosaickit.diagram.builder.constants import (
    DOT_RADIUS,
    HEADROOM,
    NAME_CHARACTER_WIDTH,
    NAME_CLEARANCE,
    NAME_DIAGONAL,
    NAME_FONT_SIZE,
    NAME_GAP,
    NAME_LINE_HEIGHT,
    ORIGIN_OFFSET,
    OVERHANG,
    PLOT_SHARE,
    TITLE_GAP,
    NudgeFor,
    Point,
    Ref,
)
from mosaickit.diagram.builder.diagram import Diagram
from mosaickit.diagram.builder.stack import PointLink, link_points, stack
from mosaickit.diagram.builder.symbols import indexed, is_symbol, primed

__all__ = [
    "DOT_RADIUS",
    "HEADROOM",
    "NAME_CHARACTER_WIDTH",
    "NAME_CLEARANCE",
    "NAME_DIAGONAL",
    "NAME_FONT_SIZE",
    "NAME_GAP",
    "NAME_LINE_HEIGHT",
    "ORIGIN_OFFSET",
    "OVERHANG",
    "PLOT_SHARE",
    "TITLE_GAP",
    "Diagram",
    "NudgeFor",
    "Point",
    "PointLink",
    "Ref",
    "indexed",
    "is_symbol",
    "link_points",
    "primed",
    "stack",
]
