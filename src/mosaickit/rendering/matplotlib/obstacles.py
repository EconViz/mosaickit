"""Turn what is already drawn on the axes into display-pixel obstacles.

Reads Matplotlib artists, not scene layer types, so anything any builder drew
(including layer types registered by other packages) is avoided.
"""

import math
from typing import Any

from mosaickit.layout import Obstacles, Rect
from mosaickit.layout.geometry import Point, Segment


def to_display(ax: Any, points: Any) -> tuple[Point, ...]:
    return tuple((float(x), float(y)) for x, y in ax.transData.transform(list(points)))


def window_rect(artist: Any, renderer: Any) -> Rect:
    box = artist.get_window_extent(renderer)
    return Rect(box.x0, box.y0, box.x1, box.y1)


def _rings(patch: Any) -> list[tuple[Point, ...]]:
    """The patch outline in display pixels, one ring per subpath."""
    return [
        tuple((float(x), float(y)) for x, y in ring)
        for ring in patch.get_path().to_polygons(patch.get_transform(), closed_only=False)
        if len(ring) >= 2
    ]


def _chain(points: tuple[Point, ...]) -> list[Segment]:
    return list(zip(points[:-1], points[1:], strict=True))


def _visible(rgba: Any) -> bool:
    return len(rgba) == 4 and rgba[3] > 0


def patch_polygon(patch: Any) -> tuple[Point, ...] | None:
    """The filled outline of a patch, or None when it has no visible fill."""
    if not (patch.get_fill() and _visible(patch.get_facecolor())):
        return None
    rings = _rings(patch)
    if not rings:
        return None
    ring = rings[0]
    return ring[:-1] if len(ring) > 3 and ring[0] == ring[-1] else ring


def marker_rects(ax: Any) -> list[Rect]:
    """The bounding square of every point drawn by a collection (scatter markers)."""
    scale = ax.figure.dpi / 72
    rects: list[Rect] = []
    for collection in ax.collections:
        offsets = collection.get_offset_transform().transform(collection.get_offsets())
        sizes = collection.get_sizes()
        for i, (x, y) in enumerate(offsets):
            # Scatter size is an area in pt²; half its square root is the radius in pt.
            radius = math.sqrt(sizes[i % len(sizes)] if len(sizes) else 0) / 2 * scale
            rects.append(Rect(x - radius, y - radius, x + radius, y + radius))
    return rects


def collect_obstacles(ax: Any, renderer: Any) -> Obstacles:
    segments: list[Segment] = []
    rects: list[Rect] = []
    polygons: list[tuple[Point, ...]] = []
    for patch in ax.patches:
        polygon = patch_polygon(patch)
        if polygon is not None and len(polygon) >= 3:
            # A filled patch is avoided as a region; its outline is not a separate line.
            polygons.append(polygon)
        elif patch.get_linewidth() > 0 and _visible(patch.get_edgecolor()):
            for ring in _rings(patch):
                segments.extend(_chain(ring))
    for line in ax.lines:
        segments.extend(_chain(to_display(ax, line.get_xydata())))
    rects.extend(marker_rects(ax))
    rects.extend(window_rect(text, renderer) for text in ax.texts if text.get_text())
    return Obstacles(tuple(segments), tuple(rects), tuple(polygons))
