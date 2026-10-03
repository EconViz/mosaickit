"""Matplotlib rendering without pyplot or global rcParams mutation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from mosaickit.colors import Color
from mosaickit.errors import RenderError
from mosaickit.rendering.matplotlib import (
    builtins as _builtins,  # noqa: F401  (registers built-in layers)
)
from mosaickit.rendering.matplotlib.artists.path_artist import rgba
from mosaickit.rendering.matplotlib.fonts import font_properties
from mosaickit.rendering.matplotlib.registry import (
    PassContext,
    builder_for,
    deferred_kind,
    passes,
)
from mosaickit.rendering.plan import _build_render_plan, _resolve_role
from mosaickit.rendering.protocol import SaveOptions


@dataclass
class MatplotlibResult:
    figure: Figure
    axes: Any
    _closed: bool = False
    _manager_number: int | str | None = None

    def show(self) -> None:
        if self._closed:
            raise RenderError("Result is closed")
        from matplotlib import pyplot as plt

        if self._manager_number is None:
            manager = plt.figure()
            manager.canvas.figure = self.figure
            self.figure.set_canvas(manager.canvas)
            self._manager_number = manager.number
        plt.show()

    def save(self, target: str | Path, **options: Any) -> list[Path]:
        return MatplotlibRenderer().save(self, Path(target), SaveOptions(**options))

    def close(self) -> None:
        if not self._closed:
            if self._manager_number is not None:
                from matplotlib import pyplot as plt

                plt.close(self._manager_number)
            self.figure.clear()
            self._closed = True


class MatplotlibRenderer:
    name = "matplotlib"

    def _draw(self, ax, scene, context) -> None:
        spec = context.spec
        ax.set_xlim(spec.x_range)
        ax.set_ylim(spec.y_range)
        ax.set_xlabel(spec.x_label)
        ax.set_ylabel(spec.y_label)
        title_style = _resolve_role(context, "title", "text").text
        assert title_style is not None
        assert isinstance(title_style.color, Color) and title_style.opacity is not None
        ax.set_title(
            spec.title or "",
            fontproperties=font_properties(title_style),
            color=rgba(title_style.color, title_style.opacity),
        )
        ax.set_axis_off()
        plan = _build_render_plan(scene, context)
        handles: dict[str, Any] = {}
        deferred: dict[type, list[Any]] = {}
        for resolved in plan.layers:
            layer = resolved.layer
            kind = deferred_kind(type(layer))
            if kind is not None:
                deferred.setdefault(kind, []).append(resolved)
                continue
            artist = builder_for(type(layer))(ax, resolved)
            artist.set_gid(layer.id)
            if layer.legend:
                handles[layer.id] = artist
        pass_context = PassContext(handles)
        for kind, run in passes():
            if kind in deferred:
                run(ax, deferred[kind], pass_context)

    def render(self, scene, context) -> MatplotlibResult:
        spec = context.spec
        figure = Figure(figsize=(spec.width, spec.height), dpi=spec.dpi)
        background = _resolve_role(context, "canvas", "region").fill
        assert background is not None
        assert isinstance(background.color, Color) and background.opacity is not None
        figure.set_facecolor(rgba(background.color, background.opacity))
        FigureCanvasAgg(figure)
        ax = figure.add_subplot(111)
        self._draw(ax, scene, context)
        return MatplotlibResult(figure, ax)

    def render_grid(self, grid, cache) -> MatplotlibResult:
        width = max((p.canvas.spec.width / p.cols for p in grid.placements), default=6)
        height = max((p.canvas.spec.height / p.rows for p in grid.placements), default=6)
        dpi = max((p.canvas.spec.dpi for p in grid.placements), default=300)
        figure = Figure(figsize=(width * grid.cols, height * grid.rows), dpi=dpi)
        FigureCanvasAgg(figure)
        slots = figure.add_gridspec(grid.rows, grid.cols)
        axes = []
        for p in grid.placements:
            ax = figure.add_subplot(slots[p.row : p.row + p.rows, p.col : p.col + p.cols])
            self._draw(ax, p.canvas.snapshot(), p.canvas._context(cache))
            axes.append(ax)
        return MatplotlibResult(figure, tuple(axes))

    def save(self, result: MatplotlibResult, target: Path, options: SaveOptions) -> list[Path]:
        if result._closed:
            raise RenderError("Cannot save a closed result")
        if target.suffix.lower() not in {".png", ".pdf", ".svg"}:
            raise RenderError(f"Matplotlib does not support {target.suffix!r}")
        result.figure.savefig(target, transparent=options.transparent)
        return [target]

    def save_animation(self, animation, path, cache):
        from mosaickit.rendering.matplotlib.animation import save_animation

        return save_animation(animation, path, self, cache)
