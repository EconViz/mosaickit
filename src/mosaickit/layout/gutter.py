"""Columns outside an axis, ordered outward: marks, outside braces, then notes.

Distances are measured outward from the axis line. Each column is as wide as the
widest thing in it; an empty column takes no space and adds no gap.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Band:
    near: float
    far: float

    @property
    def width(self) -> float:
        return self.far - self.near


@dataclass(frozen=True, slots=True)
class GutterColumns:
    marks: Band
    braces: tuple[Band, ...]  # one band per brace lane, innermost first
    notes: Band

    @property
    def extent(self) -> float:
        return max(self.marks.far, *(band.far for band in self.braces), self.notes.far)


def gutter_columns(
    mark_width: float,
    brace_widths: Sequence[float],
    note_width: float,
    *,
    start: float,
    gap: float,
) -> GutterColumns:
    """Lay out the columns from ``start`` outward, ``gap`` apart."""
    widths = [mark_width, *brace_widths, note_width]
    if any(width < 0 for width in widths):
        raise ValueError("Column widths must be non-negative")
    bands = []
    edge, used = start, False
    for width in widths:
        if width == 0:
            bands.append(Band(edge, edge))
            continue
        near = edge + gap if used else edge
        bands.append(Band(near, near + width))
        edge, used = near + width, True
    return GutterColumns(bands[0], tuple(bands[1:-1]), bands[-1])
