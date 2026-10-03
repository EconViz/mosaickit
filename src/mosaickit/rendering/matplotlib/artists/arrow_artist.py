from typing import Any

from mosaickit.rendering.matplotlib.arrows import add_arrow


def build(ax: Any, resolved: Any) -> Any:
    layer = resolved.layer
    artist = add_arrow(
        ax, layer.start, layer.end, resolved.style.stroke, layer.arrow_placement, layer.z_index
    )
    artist.set_label(layer.legend)
    if layer.label:
        ax.text(
            (layer.start[0] + layer.end[0]) / 2,
            (layer.start[1] + layer.end[1]) / 2,
            layer.label,
        )
    return artist
