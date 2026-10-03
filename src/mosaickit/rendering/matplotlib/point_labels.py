"""Measure, place, and draw point labels after everything else they must avoid."""

from collections.abc import Sequence
from typing import Any

from mosaickit.layout import Obstacles, Rect, place_point_label
from mosaickit.rendering.matplotlib.fonts import measure_text
from mosaickit.rendering.matplotlib.labels import draw_label, warn_unplaced
from mosaickit.rendering.matplotlib.obstacles import collect_obstacles, marker_rects, to_display
from mosaickit.rendering.matplotlib.registry import PassContext

PAD_PT = 1.0


def _footprint(ax: Any, point: Any) -> Rect:
    """The markers drawn at ``point`` in display pixels, or the bare point."""
    ((x, y),) = to_display(ax, [point])
    own = [rect for rect in marker_rects(ax) if rect.contains((x, y))]
    if not own:
        return Rect(x, y, x, y)
    return Rect(
        min(r.x0 for r in own),
        min(r.y0 for r in own),
        max(r.x1 for r in own),
        max(r.y1 for r in own),
    )


def _draw(ax: Any, resolved: Any, obstacles: Obstacles, renderer: Any) -> Obstacles:
    layer, style = resolved.layer, resolved.style.text
    scale = ax.figure.dpi / 72
    pad = PAD_PT * scale
    width, height = measure_text(ax, layer.text, style, renderer)
    placement = place_point_label(
        _footprint(ax, layer.point),
        (width + 2 * pad, height + 2 * pad),
        obstacles,
        Rect(*ax.bbox.extents),
        scale=scale,
    )
    if placement.violations:
        warn_unplaced(layer, placement.violations, "position beside the point")
    draw_label(ax, style, layer.text, placement.rect.center, gid=layer.id, z_index=layer.z_index)
    return obstacles.extended(rects=(placement.rect,))


def point_label_pass(ax: Any, labels: Sequence[Any], context: PassContext) -> None:
    renderer = ax.figure.canvas.get_renderer()
    obstacles = collect_obstacles(ax, renderer)
    for resolved in labels:
        obstacles = _draw(ax, resolved, obstacles, renderer)
