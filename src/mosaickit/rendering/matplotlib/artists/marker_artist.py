from typing import Any

from mosaickit.rendering.matplotlib.artists.path_artist import rgba


def _inside(ax: Any, points: Any) -> list[tuple[float, float]]:
    """Points whose centres lie in the plot range, edges included."""
    (x0, x1), (y0, y1) = sorted(ax.get_xlim()), sorted(ax.get_ylim())
    tx, ty = 1e-9 * (x1 - x0), 1e-9 * (y1 - y0)
    return [(x, y) for x, y in points if x0 - tx <= x <= x1 + tx and y0 - ty <= y <= y1 + ty]


def build(ax: Any, resolved: Any) -> Any:
    """Markers are drawn whole: one centred on the plot edge (such as a point on
    an axis) is not cut in half, and one centred outside the plot is left out."""
    layer, marker = resolved.layer, resolved.style.marker
    points = _inside(ax, layer.points)
    return ax.scatter(
        [point[0] for point in points],
        [point[1] for point in points],
        s=marker.size,
        marker=marker.shape,
        c=[rgba(marker.color, marker.opacity)],
        edgecolors=[rgba(marker.edge_color, marker.opacity)],
        linewidths=marker.edge_width,
        zorder=layer.z_index,
        label=layer.legend,
        clip_on=False,
    )
