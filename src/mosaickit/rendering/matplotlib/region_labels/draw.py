"""Measure, place, and draw one region label."""

from collections.abc import Mapping
from typing import Any

from mosaickit.errors import RenderError
from mosaickit.layout import Obstacles, Rect, fits_inside, place_callout, polylabel
from mosaickit.layout.geometry import Segment
from mosaickit.rendering.matplotlib.fonts import measure_text
from mosaickit.rendering.matplotlib.labels import draw_label, draw_leader, warn_unplaced
from mosaickit.rendering.matplotlib.obstacles import to_display

PAD_PT = 2.0


def _polygon(ax: Any, layer: Any, regions: Mapping[str, Any]) -> Any:
    """The region in display pixels: a drawn filled artist by id, or the layer's own polygon."""
    if not isinstance(layer.region, str):
        return to_display(ax, layer.region)
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
        width, height = measure_text(ax, text, style, renderer)
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
        warn_unplaced(layer, placement.violations, "callout position")
    return layer.text, placement.rect, placement.leader


def draw_region_label(
    ax: Any, resolved: Any, regions: Mapping[str, Any], obstacles: Obstacles, renderer: Any
) -> Obstacles:
    """Draw one label and return the obstacles grown by what was drawn."""
    layer, style, stroke = resolved.layer, resolved.style.text, resolved.style.stroke
    polygon = _polygon(ax, layer, regions)
    text, rect, leader = _choose(ax, layer, style, polygon, obstacles, renderer)

    draw_label(ax, style, text, rect.center, gid=layer.id, z_index=layer.z_index)
    if leader is None:
        return obstacles.extended(rects=(rect,))
    draw_leader(ax, leader, stroke, gid=f"{layer.id}.leader", z_index=layer.z_index)
    return obstacles.extended(segments=(leader,), rects=(rect,))
