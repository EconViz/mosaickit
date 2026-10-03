"""Draw braces between two points inside the plot and place their labels."""

import warnings
from collections.abc import Sequence
from typing import Any

from matplotlib.lines import Line2D

from mosaickit.errors import LayoutWarning
from mosaickit.layout import Rect
from mosaickit.layout.geometry.brace import brace_outline
from mosaickit.layout.placement.beside import place_beside
from mosaickit.layout.placement.callout import place_callout
from mosaickit.rendering.matplotlib.artists.path_artist import rgba
from mosaickit.rendering.matplotlib.fonts import font_properties, measure_text
from mosaickit.rendering.matplotlib.gutter.text import as_drawn
from mosaickit.rendering.matplotlib.obstacles import collect_obstacles, to_display
from mosaickit.rendering.matplotlib.registry import PassContext

GAP_PT = 4.0  # between the span and the brace ends, clear of point markers
DEPTH_PT = 8.0  # from the brace ends to its tip
PAD_PT = 2.0  # around the label text

_DIRECTION = {"above": 1, "below": -1, "right": 1, "left": -1}


def _draw_brace(ax: Any, resolved: Any) -> tuple[tuple[float, float], str, int, float]:
    """Draw the brace; return its tip (display px), axis, direction, and half span."""
    layer, stroke = resolved.layer, resolved.style.stroke
    scale = ax.figure.dpi / 72
    (x0, y0), (x1, y1) = to_display(ax, (layer.start, layer.end))
    direction = _DIRECTION[layer.side]
    if layer.side in ("above", "below"):
        axis, lo, hi, base = "x", x0, x1, y0 + direction * GAP_PT * scale
    else:
        axis, lo, hi, base = "y", y0, y1, x0 + direction * GAP_PT * scale
    brace = brace_outline(lo, hi, base=base, depth=DEPTH_PT * scale, direction=direction, axis=axis)
    xs, ys = zip(*ax.transData.inverted().transform(list(brace.points)), strict=True)
    ax.add_line(
        Line2D(
            xs,
            ys,
            color=rgba(stroke.color, stroke.opacity),
            linewidth=stroke.width,
            linestyle=stroke.dash.value,
            solid_capstyle="round",
            solid_joinstyle="round",
            zorder=layer.z_index,
            gid=layer.id,
            clip_on=False,
        )
    )
    return brace.tip, axis, direction, abs(hi - lo) / 2


def _tip_area(tip: Any, scale: float) -> tuple[tuple[float, float], ...]:
    """A tiny square around the brace tip: the 'region' a callout leader starts in."""
    x, y = tip
    r = 1.0 * scale
    return ((x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r))


def _draw_leader(ax: Any, resolved: Any, leader: Any) -> None:
    stroke, layer = resolved.style.stroke, resolved.layer
    xs, ys = zip(*ax.transData.inverted().transform(list(leader)), strict=True)
    ax.add_line(
        Line2D(
            xs,
            ys,
            color=rgba(stroke.color, stroke.opacity),
            linewidth=0.8,
            zorder=layer.z_index,
            gid=f"{layer.id}.leader",
            clip_on=False,
        )
    )


def _draw_label(ax: Any, resolved: Any, tip: Any, axis: str, direction: int, reach: float) -> None:
    layer, style = resolved.layer, resolved.style.text
    renderer = ax.figure.canvas.get_renderer()
    scale = ax.figure.dpi / 72
    text = as_drawn(layer.label, layer.math)
    width, height = measure_text(ax, text, style, renderer)
    pad = 2 * PAD_PT * scale
    size = (width + pad, height + pad)
    obstacles = collect_obstacles(ax, renderer)
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
        # No room right past the tip: pull the label out on a leader instead.
        callout = place_callout(_tip_area(tip, scale), size, obstacles, bounds, scale=scale)
        if callout.violations < violations:
            rect, violations, leader = callout.rect, callout.violations, callout.leader
    if leader is not None:
        _draw_leader(ax, resolved, leader)
    if violations:
        warnings.warn(
            f"SpanBraceLayer {layer.id!r}: no label position avoids every obstacle "
            f"({violations} overlaps)",
            LayoutWarning,
            stacklevel=2,
        )
    x, y = ax.transData.inverted().transform(rect.center)
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
        gid=f"{layer.id}.label",
    )


def span_brace_pass(ax: Any, braces: Sequence[Any], context: PassContext) -> None:
    # Draw every brace first, so each label avoids all of them.
    drawn = [(resolved, _draw_brace(ax, resolved)) for resolved in braces]
    for resolved, (tip, axis, direction, reach) in drawn:
        if resolved.layer.label is not None:
            _draw_label(ax, resolved, tip, axis, direction, reach)


__all__ = ["span_brace_pass"]
