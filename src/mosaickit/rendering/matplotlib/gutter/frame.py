"""One code path for both axes: positions along an axis and distances out from it.

The y axis is the plot's left edge and its gutter lies to the left; the x axis
is the bottom edge and its gutter lies below. Everything is in display pixels.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mosaickit.layout.geometry import Point


@dataclass(frozen=True, slots=True)
class AxisFrame:
    axis: str
    line: float  # display coordinate of the axis line, across the axis

    @classmethod
    def of(cls, ax: Any, axis: str) -> AxisFrame:
        return cls(axis, ax.bbox.x0 if axis == "y" else ax.bbox.y0)

    def along(self, ax: Any, value: float) -> float:
        x, y = ax.transData.transform((ax.get_xlim()[0], value) if self.axis == "y" else (value, 0))
        return float(y if self.axis == "y" else x)

    def point(self, along: float, outward: float) -> Point:
        """The display point ``outward`` pixels into the gutter (negative: into the plot)."""
        across = self.line - outward
        return (across, along) if self.axis == "y" else (along, across)

    def split(self, size: tuple[float, float]) -> tuple[float, float]:
        """A text box ``(width, height)`` as ``(along, across)`` extents."""
        width, height = size
        return (height, width) if self.axis == "y" else (width, height)

    @property
    def facing(self) -> tuple[str, str]:
        """Text alignment that puts a gutter text's axis-facing side at its anchor."""
        return ("right", "center") if self.axis == "y" else ("center", "top")
