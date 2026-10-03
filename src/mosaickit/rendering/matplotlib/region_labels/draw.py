"""Measure, place, and draw one region label."""

import warnings
from typing import Any

from matplotlib.lines import Line2D

from mosaickit.errors import LayoutWarning, RenderError
from mosaickit.layout import Obstacles, Rect, fits_inside, place_callout, polylabel
from mosaickit.layout.geometry import Segment
from mosaickit.rendering.matplotlib.artists.path_artist import rgba
from mosaickit.rendering.matplotlib.fonts import font_properties
from mosaickit.rendering.matplotlib.region_labels.obstacles import to_display

PAD_PT = 2.0


def _measure(ax: Any, text: str, style: Any, renderer: Any) -> tuple[float, float]:
    probe = ax.text(0, 0, text, fontproperties=font_properties(style), ha="center", va="center")
    box = probe.get_window_extent(renderer)
    probe.remove()
    return box.width, box.height


def _boundary(layer: Any, regions: dict[str, Any]) -> Any:
    if not isinstance(layer.region, str):
        return layer.region
    if layer.region not in regions:
        raise RenderError(
            f"RegionLabelLayer {layer.id!r} references unknown region {layer.region!r}"
        )
    return regions[layer.region]


def _choose(
    ax: Any, layer: Any, style: Any, polygon: Any, obstacles: Obstacles, renderer: Any
) -> tuple[str, Rect, Segment | None]:
    scale = ax.figure.dpi / 72
    pad = PAD_PT * scale
    bounds = Rect(*ax.bbox.extents)

    def padded(text: str) -> tuple[float, float]:
        width, height = _measure(ax, text, style, renderer)
        return width + 2 * pad, height + 2 * pad

    if layer.placement != "callout":
        for text in (layer.text, layer.short_text):
            if text is not None:
                rect = fits_inside(polygon, padded(text), obstacles, bounds)
                if rect is not None:
                    return text, rect, None
        if layer.placement == "inside":
            text = layer.short_text or layer.text
            return text, Rect.centered(polylabel(polygon), *padded(text)), None

    placement = place_callout(polygon, padded(layer.text), obstacles, bounds, scale=scale)
    if placement.violations:
        warnings.warn(
            f"RegionLabelLayer {layer.id!r}: no callout position avoids every obstacle "
            f"({placement.violations} overlaps)",
            LayoutWarning,
            stacklevel=2,
        )
    return layer.text, placement.rect, placement.leader


def draw_region_label(
    ax: Any, resolved: Any, regions: dict[str, Any], obstacles: Obstacles, renderer: Any
) -> Obstacles:
    """Draw one label and return the obstacles grown by what was drawn."""
    layer, style, stroke = resolved.layer, resolved.style.text, resolved.style.stroke
    polygon = to_display(ax, _boundary(layer, regions))
    text, rect, leader = _choose(ax, layer, style, polygon, obstacles, renderer)

    to_data = ax.transData.inverted()
    x, y = to_data.transform(rect.center)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        multialignment="center",
        fontproperties=font_properties(style),
        color=rgba(style.color, style.opacity),
        rotation=style.rotation,
        zorder=layer.z_index,
        gid=layer.id,
    )
    if leader is None:
        return obstacles.extended(rects=(rect,))
    (x0, y0), (x1, y1) = to_data.transform(list(leader))
    ax.add_line(
        Line2D(
            [x0, x1],
            [y0, y1],
            color=rgba(stroke.color, stroke.opacity),
            linewidth=stroke.width,
            linestyle=stroke.dash.value,
            zorder=layer.z_index,
            gid=f"{layer.id}.leader",
        )
    )
    return obstacles.extended(segments=(leader,), rects=(rect,))
