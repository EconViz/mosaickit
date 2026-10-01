from typing import Any

from mosaickit.rendering.matplotlib.artists.path_artist import rgba


def build(ax: Any, resolved: Any) -> Any:
    layer, marker = resolved.layer, resolved.style.marker
    return ax.scatter(
        [point.x for point in layer.points],
        [point.y for point in layer.points],
        s=marker.size,
        marker=marker.shape,
        c=[rgba(marker.color, marker.opacity)],
        edgecolors=[rgba(marker.edge_color, marker.opacity)],
        linewidths=marker.edge_width,
        zorder=layer.z_index,
        label=layer.legend,
    )
