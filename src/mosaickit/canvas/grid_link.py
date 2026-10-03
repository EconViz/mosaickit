"""A straight line joining points in two cells of a grid."""

from __future__ import annotations

from dataclasses import dataclass

from mosaickit.errors import ConfigurationError
from mosaickit.styles import Stroke

Point = tuple[float, float]


@dataclass(frozen=True, slots=True)
class GridLink:
    """A line from ``start`` in cell ``start_cell`` to ``end`` in cell ``end_cell``.

    Each point is in its own cell's data coordinates; cells are numbered in
    placement order. The line is drawn over the figure, across the gaps between
    cells. Its style is ``role`` resolved in the start cell's theme, with
    ``stroke`` on top.
    """

    start_cell: int
    start: Point
    end_cell: int
    end: Point
    role: str = "link"
    stroke: Stroke | None = None

    def check(self, cells: int) -> None:
        for name in ("start_cell", "end_cell"):
            index = getattr(self, name)
            if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < cells:
                raise ConfigurationError(
                    f"GridLink.{name} must be a cell index below {cells}, got {index!r}"
                )
