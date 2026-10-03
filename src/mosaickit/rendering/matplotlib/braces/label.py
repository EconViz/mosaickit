"""Place a brace's label past its tip, covering nothing.

Nearest spots past the tip come first, sliding along the span; when none is free
the label moves out on a leader instead.
"""

from typing import Any

from mosaickit.layout import Obstacles, Rect
from mosaickit.layout.geometry import Point
from mosaickit.layout.placement.beside import place_beside
from mosaickit.layout.placement.callout import place_callout
from mosaickit.rendering.matplotlib.labels import draw_label, draw_leader, warn_unplaced
from mosaickit.rendering.matplotlib.obstacles import window_rect


def _tip_area(tip: Point, scale: float) -> tuple[Point, ...]:
    """A tiny square around the tip: where a callout leader starts."""
    x, y = tip
    r = 1.0 * scale
    return ((x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r))


def place_brace_label(
    ax: Any,
    resolved: Any,
    text: str,
    size: tuple[float, float],
    tip: Point,
    *,
    axis: str,
    direction: int,
    reach: float,
    obstacles: Obstacles,
    renderer: Any,
) -> Obstacles:
    """Draw the label (and any leader) and return the obstacles grown by them.

    ``axis`` is the axis the brace's span runs along and ``direction`` (+1 / -1)
    the side its tip points to; ``reach`` is how far, in px, the label may slide
    along the span from the tip.
    """
    layer = resolved.layer
    scale = ax.figure.dpi / 72
    bounds = Rect(*ax.bbox.extents)
    rect, violations = place_beside(
        tip,
        size,
        axis=axis,
        direction=direction,
        reach=reach,
        obstacles=obstacles,
        bounds=bounds,
        scale=scale,
    )
    leader = None
    if violations:
        callout = place_callout(_tip_area(tip, scale), size, obstacles, bounds, scale=scale)
        if callout.violations < violations:
            rect, violations, leader = callout.rect, callout.violations, callout.leader
    if violations:
        warn_unplaced(layer, violations, "label position")
    if leader is not None:
        draw_leader(
            ax, leader, resolved.style.stroke, gid=f"{layer.id}.leader", z_index=layer.z_index
        )
    artist = draw_label(
        ax, resolved.style.text, text, rect.center, gid=f"{layer.id}.label", z_index=layer.z_index
    )
    grown = obstacles.extended(rects=(window_rect(artist, renderer),))
    return grown if leader is None else grown.extended(segments=(leader,))
