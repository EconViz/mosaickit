"""Turn already-drawn scene content into display-pixel obstacles."""

import math
from typing import Any

from mosaickit.layout import Obstacles, Rect
from mosaickit.scene import ArrowLayer, FillLayer, MarkerLayer, PathLayer


def to_display(ax: Any, points: Any) -> tuple[tuple[float, float], ...]:
    return tuple((float(x), float(y)) for x, y in ax.transData.transform(list(points)))


def window_rect(artist: Any, renderer: Any) -> Rect:
    box = artist.get_window_extent(renderer)
    return Rect(box.x0, box.y0, box.x1, box.y1)


def collect_obstacles(ax: Any, resolved_layers: Any, texts: Any, renderer: Any) -> Obstacles:
    scale = ax.figure.dpi / 72
    segments: list = []
    rects: list = []
    polygons: list = []
    for resolved in resolved_layers:
        layer = resolved.layer
        if isinstance(layer, PathLayer):
            points = to_display(ax, layer.path)
            segments.extend(zip(points[:-1], points[1:], strict=True))
        elif isinstance(layer, ArrowLayer):
            segments.append(to_display(ax, (layer.start, layer.end)))
        elif isinstance(layer, FillLayer):
            polygons.append(to_display(ax, layer.boundary))
        elif isinstance(layer, MarkerLayer):
            # Scatter size is an area in pt²; half its square root is the radius in pt.
            radius = math.sqrt(resolved.style.marker.size) / 2 * scale
            for x, y in to_display(ax, layer.points):
                rects.append(Rect(x - radius, y - radius, x + radius, y + radius))
    rects.extend(window_rect(artist, renderer) for artist in texts)
    return Obstacles(tuple(segments), tuple(rects), tuple(polygons))
