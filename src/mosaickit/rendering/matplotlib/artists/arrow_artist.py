from typing import Any

from matplotlib.patches import PathPatch

from mosaickit.rendering.matplotlib.arrows import add_arrow, add_path_arrows
from mosaickit.rendering.matplotlib.artists.path_artist import mpl_path, rgba
from mosaickit.styles import DashStyle


def _dashed(ax: Any, layer: Any, stroke: Any) -> Any:
    """A dashed shaft with solid heads, so the heads keep their shape."""
    path = mpl_path((layer.start, layer.end))
    shaft = PathPatch(
        path,
        facecolor="none",
        edgecolor=rgba(stroke.color, stroke.opacity),
        linewidth=stroke.width,
        linestyle=stroke.dash.value,
        zorder=layer.z_index,
        clip_on=False,
    )
    ax.add_patch(shaft)
    add_path_arrows(ax, path, stroke, layer.arrow_placement, layer.z_index)
    return shaft


def build(ax: Any, resolved: Any) -> Any:
    layer, stroke = resolved.layer, resolved.style.stroke
    if stroke.dash not in (None, DashStyle.SOLID):
        artist = _dashed(ax, layer, stroke)
    else:
        artist = add_arrow(ax, layer.start, layer.end, stroke, layer.arrow_placement, layer.z_index)
    artist.set_label(layer.legend)
    if layer.label:
        ax.text(
            (layer.start[0] + layer.end[0]) / 2,
            (layer.start[1] + layer.end[1]) / 2,
            layer.label,
        )
    return artist
