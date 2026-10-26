"""Size of the axes a :class:`~mosaickit.CanvasGrid` cell gets under Matplotlib."""

from __future__ import annotations

from typing import TYPE_CHECKING

from matplotlib import rcParams

from mosaickit.errors import ConfigurationError

if TYPE_CHECKING:
    from mosaickit.canvas.grid import CanvasGrid


def grid_axes_size(grid: CanvasGrid, cell: int) -> tuple[float, float]:
    """Width and height in inches of the axes of placement ``cell`` once ``grid`` is rendered.

    Reflects the grid's :class:`~mosaickit.GridSpacing` (Matplotlib's own defaults for
    the fields left unset) and the number of rows and columns the cell spans.
    """
    if isinstance(cell, bool) or not isinstance(cell, int) or not 0 <= cell < len(grid.placements):
        raise ConfigurationError(f"grid_axes_size: cell {cell!r} does not exist")
    spacing = grid.spacing
    left = right = bottom = top = None
    if spacing.outer is not None:
        left = bottom = spacing.outer
        right = top = 1 - spacing.outer
    else:
        left, right = rcParams["figure.subplot.left"], rcParams["figure.subplot.right"]
        bottom, top = rcParams["figure.subplot.bottom"], rcParams["figure.subplot.top"]
    wspace = (
        spacing.column_gap if spacing.column_gap is not None else rcParams["figure.subplot.wspace"]
    )
    hspace = spacing.row_gap if spacing.row_gap is not None else rcParams["figure.subplot.hspace"]
    figure_width, figure_height = grid.figure_size
    placement = grid.placements[cell]

    def extent(units: int, gap: float) -> float:
        return units + gap * (units - 1)

    width = (
        figure_width * (right - left) * extent(placement.cols, wspace) / extent(grid.cols, wspace)
    )
    height = (
        figure_height * (top - bottom) * extent(placement.rows, hspace) / extent(grid.rows, hspace)
    )
    return (width, height)
