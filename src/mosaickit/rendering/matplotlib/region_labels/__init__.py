"""Region labels are placed after every builder and point label so they can avoid them."""

from collections.abc import Sequence
from typing import Any

from mosaickit.rendering.matplotlib.obstacles import (
    collect_obstacles,
    patch_polygon,
)
from mosaickit.rendering.matplotlib.region_labels.draw import draw_region_label
from mosaickit.rendering.matplotlib.registry import PassContext


def region_label_pass(ax: Any, labels: Sequence[Any], context: PassContext) -> None:
    renderer = ax.figure.canvas.get_renderer()
    obstacles = collect_obstacles(ax, renderer)
    regions = {}
    for patch in ax.patches:
        polygon = patch_polygon(patch)
        if patch.get_gid() and polygon is not None:
            regions[patch.get_gid()] = polygon
    for resolved in labels:
        obstacles = draw_region_label(ax, resolved, regions, obstacles, renderer)


__all__ = ["region_label_pass"]
