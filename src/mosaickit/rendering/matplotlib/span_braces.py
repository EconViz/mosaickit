"""Braces between two points inside the plot: outline, then label past the tip."""

from collections.abc import Sequence
from typing import Any

from mosaickit.layout.geometry import Brace, brace_outline
from mosaickit.rendering.matplotlib.braces import draw_brace, place_brace_label
from mosaickit.rendering.matplotlib.fonts import measure_text
from mosaickit.rendering.matplotlib.gutter.text import as_drawn
from mosaickit.rendering.matplotlib.obstacles import collect_obstacles, to_display
from mosaickit.rendering.matplotlib.registry import PassContext

GAP_PT = 4.0  # between the span and the brace ends, clear of point markers
DEPTH_PT = 8.0  # from the brace ends to its tip
PAD_PT = 2.0  # around the label text

_DIRECTION = {"above": 1, "below": -1, "right": 1, "left": -1}


def _outline(ax: Any, layer: Any) -> tuple[Brace, str, int, float]:
    """The brace in display px, the axis its span runs along, its direction, and
    half the span length."""
    scale = ax.figure.dpi / 72
    (x0, y0), (x1, y1) = to_display(ax, (layer.start, layer.end))
    direction = _DIRECTION[layer.side]
    if layer.side in ("above", "below"):
        axis, lo, hi, base = "x", x0, x1, y0 + direction * GAP_PT * scale
    else:
        axis, lo, hi, base = "y", y0, y1, x0 + direction * GAP_PT * scale
    brace = brace_outline(lo, hi, base=base, depth=DEPTH_PT * scale, direction=direction, axis=axis)
    return brace, axis, direction, abs(hi - lo) / 2


def span_brace_pass(ax: Any, braces: Sequence[Any], context: PassContext) -> None:
    renderer = ax.figure.canvas.get_renderer()
    pad = 2 * PAD_PT * ax.figure.dpi / 72
    # Draw every brace first, so each label avoids all of them.
    drawn = []
    for resolved in braces:
        brace, axis, direction, reach = _outline(ax, resolved.layer)
        draw_brace(ax, resolved, brace)
        drawn.append((resolved, brace.tip, axis, direction, reach))
    obstacles = collect_obstacles(ax, renderer)
    for resolved, tip, axis, direction, reach in drawn:
        layer = resolved.layer
        if layer.label is None:
            continue
        text = as_drawn(layer.label, layer.math)
        width, height = measure_text(ax, text, resolved.style.text, renderer)
        obstacles = place_brace_label(
            ax,
            resolved,
            text,
            (width + pad, height + pad),
            tip,
            axis=axis,
            direction=direction,
            reach=reach,
            obstacles=obstacles,
            renderer=renderer,
        )


__all__ = ["span_brace_pass"]
