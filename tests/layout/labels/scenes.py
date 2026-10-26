"""Shared scenes of the label tests."""

from __future__ import annotations

from mosaickit.layout import Rect
from mosaickit.layout.labels import Label, Obstacle

CANVAS = Rect(0.0, 0.0, 360.0, 280.0)


def lm_lines(
    shift: float = 14.0, name_size: tuple[float, float] = (64.0, 38.0)
) -> tuple[list[Label], list[Obstacle]]:
    """Three parallel rising lines p0/p1/p2 shifted in x, each ending at the right of its own
    start, with fraction-sized names: the macro-viz five_panel_expenditure case."""
    labels, obstacles = [], []
    for i in range(3):
        start = (40.0 + i * shift * 3, 30.0)
        end = (300.0 + i * shift, 230.0 - i * 6.0)
        obstacles.append(Obstacle.polyline([start, end], owner=f"p{i}"))
        labels.append(Label(f"p{i}", end, name_size, owner=f"p{i}"))
    return labels, obstacles
