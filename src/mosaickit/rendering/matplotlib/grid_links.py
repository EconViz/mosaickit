"""Draw grid links over a figure, from one cell's data space to another's."""

from __future__ import annotations

from typing import Any

from matplotlib.patches import ConnectionPatch

from mosaickit.colors import Color
from mosaickit.rendering.matplotlib.artists.path_artist import rgba
from mosaickit.rendering.plan import _bind_palette, _resolve_role
from mosaickit.themes import StyleBundle


def draw_grid_links(figure: Any, axes: tuple[Any, ...], contexts: tuple[Any, ...], links) -> None:
    for link in links:
        context = contexts[link.start_cell]
        style = _resolve_role(context, link.role, "primary")
        if link.stroke is not None:
            style = _bind_palette(
                StyleBundle(stroke=link.stroke).merged_over(style), context.palette, link.role
            )
        stroke = style.stroke
        assert stroke is not None and isinstance(stroke.color, Color)
        assert stroke.opacity is not None and stroke.dash is not None
        figure.add_artist(
            ConnectionPatch(
                xyA=link.start,
                coordsA=axes[link.start_cell].transData,
                xyB=link.end,
                coordsB=axes[link.end_cell].transData,
                color=rgba(stroke.color, stroke.opacity),
                linewidth=stroke.width,
                linestyle=stroke.dash.value,
                zorder=0,
            )
        )
