"""Preserve native cubic control points in Matplotlib paths."""

from __future__ import annotations

from typing import Any

from matplotlib.patches import PathPatch
from matplotlib.path import Path

from mosaickit.colors import Color
from mosaickit.rendering.matplotlib.arrows import add_path_arrows


def mpl_path(geometry: Any, *, closed: bool = False) -> Path:
    vertices = list(geometry)
    codes = [Path.MOVETO] + [Path.LINETO] * (len(vertices) - 1)
    if closed:
        vertices.append(vertices[0])
        codes.append(Path.CLOSEPOLY)
    return Path(vertices, codes)


def rgba(color: Color, opacity: float) -> tuple[float, float, float, float]:
    return color.red, color.green, color.blue, color.alpha * opacity


def build(ax: Any, resolved: Any) -> Any:
    layer, stroke = resolved.layer, resolved.style.stroke
    path = mpl_path(layer.path)
    patch = PathPatch(
        path,
        facecolor="none",
        edgecolor=rgba(stroke.color, stroke.opacity),
        linewidth=stroke.width,
        linestyle=stroke.dash.value,
        zorder=layer.z_index,
        label=layer.legend,
    )
    ax.add_patch(patch)
    if stroke.arrow:
        add_path_arrows(ax, path, stroke, layer.arrow_placement, layer.z_index)
    return patch
