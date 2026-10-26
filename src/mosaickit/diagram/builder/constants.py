"""Types and tuning constants of the diagram builder."""

from __future__ import annotations

from collections.abc import Callable

from mosaickit.scene import Layer
from mosaickit.styles.nudge import Nudge

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
NAME_DIAGONAL = 1.0
"""Share of the name gap used on a diagonal side (1: as far as on a straight side)."""
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
