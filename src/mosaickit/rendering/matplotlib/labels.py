"""Draw placed labels and their leaders; report labels that found no free spot."""

import warnings
from typing import Any

from matplotlib.lines import Line2D

from mosaickit.errors import LayoutWarning
from mosaickit.layout.geometry import Point, Segment
from mosaickit.rendering.matplotlib.artists.path_artist import rgba
from mosaickit.rendering.matplotlib.fonts import font_properties


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
