"""Region labels are placed after every other layer so they can avoid it."""

from typing import Any

from mosaickit.rendering.matplotlib.region_labels.draw import draw_region_label
from mosaickit.rendering.matplotlib.region_labels.obstacles import collect_obstacles
from mosaickit.scene import FillLayer


def place_region_labels(ax: Any, plan_layers: Any, labels: Any, texts: Any) -> None:
    renderer = ax.figure.canvas.get_renderer()
    obstacles = collect_obstacles(ax, plan_layers, texts, renderer)
    regions = {r.layer.id: r.layer.boundary for r in plan_layers if isinstance(r.layer, FillLayer)}
    for resolved in labels:
        obstacles = draw_region_label(ax, resolved, regions, obstacles, renderer)


__all__ = ["place_region_labels"]
