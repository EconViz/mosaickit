"""Draw placed labels and their leaders; report labels that found no free spot."""

import warnings
from typing import Any

from matplotlib.lines import Line2D

from mosaickit.errors import LayoutWarning
from mosaickit.layout import Rect, follow_leader
from mosaickit.layout.geometry import Point, Segment
from mosaickit.rendering.matplotlib.artists.path_artist import rgba
from mosaickit.rendering.matplotlib.fonts import font_properties
from mosaickit.rendering.matplotlib.math_text import draw_math
from mosaickit.rendering.matplotlib.typesetting import typeset


def draw_label(
    ax: Any,
    style: Any,
    text: str,
    at: Point,
    *,
    gid: str,
    z_index: float,
    align: tuple[str, str] = ("center", "center"),
) -> Any:
    """Text aligned at the display point ``at``; returns the Matplotlib text."""
    x, y = ax.transData.inverted().transform(at)
    layout = typeset(text, style)
    if layout is not None:
        return draw_math(
            ax,
            layout,
            (x, y),
            color=rgba(style.color, style.opacity),
            rotation=style.rotation,
            zorder=z_index,
            align=align,
            gid=gid,
        )
    return ax.text(
        x,
        y,
        text,
        ha=align[0],
        va=align[1],
        multialignment=align[0],
        fontproperties=font_properties(style),
        color=rgba(style.color, style.opacity),
        rotation=style.rotation,
        zorder=z_index,
        gid=gid,
    )


def nudged(
    ax: Any, nudge: Any, rect: Rect, leader: Segment | None = None
) -> tuple[Rect, Segment | None]:
    """``rect`` (and the ``leader`` pointing at it) moved by ``nudge`` points, in display pixels.

    Placement has already happened; the nudge only fine-tunes it. Points become pixels at the
    figure DPI, the scale placement itself uses. No nudge, or a zero one, changes nothing.
    """
    if nudge is None or nudge.is_zero:
        return rect, leader
    scale = ax.figure.dpi / 72
    moved = rect.shifted(nudge.dx * scale, nudge.dy * scale)
    return moved, None if leader is None else follow_leader(leader, moved, scale=scale)


def draw_leader(ax: Any, leader: Segment, stroke: Any, *, gid: str, z_index: float) -> Any:
    """A straight leader between two display points, drawn with ``stroke``."""
    xs, ys = zip(*ax.transData.inverted().transform(list(leader)), strict=True)
    line = Line2D(
        xs,
        ys,
        color=rgba(stroke.color, stroke.opacity),
        linewidth=stroke.width,
        linestyle=stroke.dash.value,
        zorder=z_index,
        gid=gid,
        clip_on=False,
    )
    ax.add_line(line)
    return line


def warn_unplaced(layer: Any, violations: int, what: str = "position") -> None:
    """Warn that ``layer``'s label covers something because nothing was free."""
    warnings.warn(
        f"{type(layer).__name__} {layer.id!r}: no {what} avoids every obstacle "
        f"({violations} overlaps)",
        LayoutWarning,
        stacklevel=3,
    )
