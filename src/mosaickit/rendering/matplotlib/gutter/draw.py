"""Draw gutter texts, brace outlines, and inside brace labels."""

import warnings
from typing import Any

from matplotlib.lines import Line2D

from mosaickit.errors import LayoutWarning
from mosaickit.layout import Obstacles, Rect
from mosaickit.layout.geometry import Point
from mosaickit.layout.placement import place_beside
from mosaickit.rendering.matplotlib.artists.path_artist import rgba
from mosaickit.rendering.matplotlib.fonts import font_properties
from mosaickit.rendering.matplotlib.gutter.frame import AxisFrame
from mosaickit.rendering.matplotlib.gutter.place import GutterText, PlacedBrace
from mosaickit.rendering.matplotlib.region_labels.obstacles import window_rect


def _text(ax: Any, resolved: Any, text: str, at: Point, align: tuple[str, str], gid: str) -> Any:
    style = resolved.style.text
    x, y = ax.transData.inverted().transform(at)
    return ax.text(
        x,
        y,
        text,
        ha=align[0],
        va=align[1],
        multialignment=align[0],
        fontproperties=font_properties(style),
        color=rgba(style.color, style.opacity),
        zorder=resolved.layer.z_index,
        gid=gid,
        clip_on=False,
    )


def draw_text(ax: Any, frame: AxisFrame, item: GutterText) -> Any:
    return _text(ax, item.resolved, item.text, item.anchor, frame.facing, item.gid)


def draw_brace(ax: Any, placed: PlacedBrace) -> Any:
    stroke, layer = placed.resolved.style.stroke, placed.resolved.layer
    xs, ys = zip(*ax.transData.inverted().transform(list(placed.outline.points)), strict=True)
    line = Line2D(
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
    ax.add_line(line)
    return line


def draw_inside_label(
    ax: Any,
    frame: AxisFrame,
    placed: PlacedBrace,
    text: str,
    size: tuple[float, float],
    obstacles: Obstacles,
    renderer: Any,
) -> Obstacles:
    """Place the label beside the brace tip covering nothing; return grown obstacles."""
    layer = placed.resolved.layer
    rect, violations = place_beside(
        placed.outline.tip,
        size,
        axis=frame.axis,
        direction=1,
        reach=placed.reach,
        obstacles=obstacles,
        bounds=Rect(*ax.bbox.extents),
        scale=ax.figure.dpi / 72,
    )
    if violations:
        warnings.warn(
            f"BraceLayer {layer.id!r}: no label position avoids every obstacle "
            f"({violations} overlaps)",
            LayoutWarning,
            stacklevel=2,
        )
    artist = _text(
        ax, placed.resolved, text, rect.center, ("center", "center"), f"{layer.id}.label"
    )
    return obstacles.extended(rects=(window_rect(artist, renderer),))
