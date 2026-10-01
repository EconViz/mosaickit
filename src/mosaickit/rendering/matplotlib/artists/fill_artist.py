from typing import Any

from matplotlib.patches import PathPatch

from mosaickit.rendering.matplotlib.artists.path_artist import mpl_path, rgba


def build(ax: Any, resolved: Any) -> Any:
    layer, fill, stroke = resolved.layer, resolved.style.fill, resolved.style.stroke
    patch = PathPatch(
        mpl_path(layer.boundary, closed=True),
        facecolor=rgba(fill.color, fill.opacity),
        edgecolor=rgba(stroke.color, stroke.opacity),
        linewidth=stroke.width,
        linestyle=stroke.dash.value,
        hatch=fill.hatch,
        zorder=layer.z_index,
        label=layer.legend,
    )
    ax.add_patch(patch)
    return patch
