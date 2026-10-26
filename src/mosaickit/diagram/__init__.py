"""A small declarative builder for theory diagrams: axes, curves, named points, guides."""

from mosaickit.diagram._names import (
    DEFAULT_NAME_ORDER,
    RISING_NAME_ORDER,
    TEX_LAYOUT_COMMANDS,
    TextSize,
)
from mosaickit.diagram._text_size import (
    DEFAULT_TEXT_SIZE_FACTORS,
    TextSizeFactors,
    estimate_text_size,
)
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
    "DEFAULT_TEXT_SIZE_FACTORS",
    "RISING_NAME_ORDER",
    "TEX_LAYOUT_COMMANDS",
    "Diagram",
    "PointLink",
    "TextSize",
    "TextSizeFactors",
    "estimate_text_size",
    "indexed",
    "is_symbol",
    "link_points",
    "primed",
    "stack",
]
