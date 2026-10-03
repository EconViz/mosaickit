from typing import Any

from mosaickit.rendering.matplotlib.artists.path_artist import rgba
from mosaickit.rendering.matplotlib.fonts import font_properties
from mosaickit.scene.text import TEXT_ANCHORS


def build(ax: Any, resolved: Any) -> Any:
    layer, style = resolved.layer, resolved.style.text
    text = str(layer.text)
    if layer.math and not (text.startswith("$") and text.endswith("$")):
        text = f"${text}$"
    horizontal, vertical = TEXT_ANCHORS[layer.anchor]
    return ax.annotate(
        text,
        layer.position,
        xytext=layer.offset,
        textcoords="offset points",
        ha=horizontal,
        va=vertical,
        color=rgba(style.color, style.opacity),
        fontproperties=font_properties(style),
        rotation=style.rotation,
        zorder=layer.z_index,
    )
