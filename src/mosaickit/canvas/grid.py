"""Validated grid placement with real row and column spans."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mosaickit.canvas.canvas import Canvas
from mosaickit.canvas.grid_link import GridLink
from mosaickit.canvas.layout import Layout
from mosaickit.canvas.span import Span
from mosaickit.errors import ConfigurationError, RenderError
from mosaickit.parameter import ParameterValues
from mosaickit.rendering import RenderCache, Renderer, RendererRegistry, SaveOptions


@dataclass(frozen=True, slots=True)
class _Placement:
    canvas: Canvas
    row: int
    col: int
    rows: int
    cols: int


class CanvasGrid:
    def __init__(
        self,
        cells: Any,
        rows: int | None = None,
        cols: int | None = None,
        shape: tuple[int, int] | None = None,
        links: Sequence[GridLink] = (),
    ) -> None:
        if shape is not None:
            if rows is not None or cols is not None or len(shape) != 2:
                raise ConfigurationError("Use shape=(rows, cols) or rows/cols, not both")
            rows, cols = shape
        for name, value in (("rows", rows), ("cols", cols)):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 1
            ):
                raise ConfigurationError(f"CanvasGrid.{name} must be a positive integer")
        cells = list(cells)
        if not cells:
            raise ConfigurationError("CanvasGrid requires at least one cell")
        nested = isinstance(cells[0], (list, tuple))
        if nested:
            if not all(isinstance(row, (list, tuple)) for row in cells):
                raise ConfigurationError("CanvasGrid cannot mix rows and flat cells")
            matrix = [list(row) for row in cells]
            rows = rows if rows is not None else len(matrix)
            if len(matrix) > rows:
                raise ConfigurationError(f"Grid has {len(matrix)} rows; expected at most {rows}")
            cols = (
                cols
                if cols is not None
                else max(
                    sum(cell.cols if isinstance(cell, Span) else 1 for cell in row)
                    for row in matrix
                )
            )
        else:
            if any(isinstance(cell, Span) and cell.rows != 1 for cell in cells):
                raise ConfigurationError("Row spans require nested grid rows")
            count = sum(cell.cols if isinstance(cell, Span) else 1 for cell in cells)
            cols = (
                cols
                if cols is not None
                else (math.ceil(count / rows) if rows else math.ceil(math.sqrt(count)))
            )
            rows = rows if rows is not None else math.ceil(count / cols)
            if count > rows * cols:
                raise ConfigurationError(
                    f"Grid has {count} cells; shape ({rows}, {cols}) is too small"
                )
            matrix = [[]]
            width = 0
            for cell in cells:
                span_width = cell.cols if isinstance(cell, Span) else 1
                if width + span_width > cols:
                    matrix.append([])
                    width = 0
                matrix[-1].append(cell)
                width += span_width
        if not cols:
            raise ConfigurationError("CanvasGrid rows cannot all be empty")
        occupied: set[tuple[int, int]] = set()
        placements = []
        for row_index, row in enumerate(matrix):
            cursor = 0
            for cell_index, cell in enumerate(row):
                while (row_index, cursor) in occupied:
                    cursor += 1
                span = cell if isinstance(cell, Span) else Span(cell) if cell is not None else None
                height, width = (span.rows, span.cols) if span else (1, 1)
                if cursor + width > cols or row_index + height > rows:
                    raise ConfigurationError(
                        f"Grid row {row_index}, cell {cell_index}: span "
                        f"({height}, {width}) exceeds shape ({rows}, {cols})"
                    )
                region = {
                    (r, c)
                    for r in range(row_index, row_index + height)
                    for c in range(cursor, cursor + width)
                }
                if region & occupied:
                    raise ConfigurationError(
                        f"Grid row {row_index}, cell {cell_index}: overlapping span"
                    )
                occupied.update(region)
                if span:
                    placements.append(
                        _Placement(span.canvas.copy(), row_index, cursor, height, width)
                    )
                cursor += width
        if nested:
            for row_index in range(rows):
                missing = [col for col in range(cols) if (row_index, col) not in occupied]
                if missing:
                    raise ConfigurationError(
                        f"Grid row {row_index}: missing columns {missing}; use None for empty cells"
                    )
        self.rows, self.cols = rows, cols
        self.placements = tuple(placements)
        for link in links:
            link.check(len(self.placements))
        self.links = tuple(links)

    @classmethod
    def sweep(
        cls, template: Canvas, values: ParameterValues, *, cols: int | None = None
    ) -> CanvasGrid:
        return cls([template.bind(values.parameter, value) for value in values.values], cols=cols)

    @classmethod
    def from_layout(cls, canvases: list[Canvas], layout: Layout) -> CanvasGrid:
        if layout == Layout.TOP_TWO_BOTTOM_ONE:
            if len(canvases) != 3:
                raise ConfigurationError("TOP_TWO_BOTTOM_ONE requires 3 canvases")
            return cls([[canvases[0], canvases[1]], [Span(canvases[2], cols=2)]])
        if layout == Layout.TOP_ONE_BOTTOM_TWO:
            if len(canvases) != 3:
                raise ConfigurationError("TOP_ONE_BOTTOM_TWO requires 3 canvases")
            return cls([[Span(canvases[0], cols=2)], [canvases[1], canvases[2]]])
        shapes = {
            Layout.SINGLE: (1, 1),
            Layout.STACKED: (2, 1),
            Layout.SIDE_BY_SIDE: (1, 2),
            Layout.GRID_2X2: (2, 2),
            Layout.GRID_3X3: (3, 3),
        }
        return cls(canvases, shape=shapes[layout])

    def _renderer(self, renderer: Renderer | str | None) -> Renderer:
        if renderer is None:
            return (
                self.placements[0].canvas._renderer()
                if self.placements
                else RendererRegistry().get("matplotlib")
            )
        return RendererRegistry().get(renderer) if isinstance(renderer, str) else renderer

    def render(
        self, *, renderer: Renderer | str | None = None, cache: RenderCache | None = None
    ) -> Any:
        selected = self._renderer(renderer)
        if not hasattr(selected, "render_grid"):
            raise RenderError(f"Renderer {selected.name!r} does not support grids")
        return selected.render_grid(self, cache if cache is not None else RenderCache())

    def save(
        self,
        target: str | Path,
        *,
        renderer: Renderer | str | None = None,
        cache: RenderCache | None = None,
        **options: Any,
    ) -> list[Path]:
        target = Path(target)
        if target.suffix.lower() not in {".png", ".pdf", ".svg"}:
            raise RenderError(f"Unsupported output format: {target.suffix!r}")
        selected = self._renderer(renderer)
        result = self.render(renderer=selected, cache=cache)
        try:
            return selected.save(result, target, SaveOptions(**options))
        finally:
            if hasattr(result, "close"):
                result.close()
