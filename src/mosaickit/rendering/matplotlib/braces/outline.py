"""Draw a brace outline computed in display pixels."""

from typing import Any

from matplotlib.lines import Line2D

from mosaickit.layout.geometry import Brace
from mosaickit.rendering.matplotlib.artists.path_artist import rgba


def draw_brace(ax: Any, resolved: Any, brace: Brace) -> Any:
    """The brace as one rounded line, styled by the layer's resolved stroke."""
    stroke, layer = resolved.style.stroke, resolved.layer
    xs, ys = zip(*ax.transData.inverted().transform(list(brace.points)), strict=True)
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
