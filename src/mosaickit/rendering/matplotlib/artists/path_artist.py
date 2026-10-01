"""Preserve native cubic control points in Matplotlib paths."""

from __future__ import annotations

from typing import Any

from bezierkit import CubicBezierSegment, PiecewiseBezier
from matplotlib.patches import PathPatch
from matplotlib.path import Path

from mosaickit.colors import Color
from mosaickit.rendering.matplotlib.arrows import add_path_arrows


def mpl_path(geometry: Any, *, closed: bool = False) -> Path:
    vertices, codes = [], []
    if isinstance(geometry, CubicBezierSegment):
        geometry = PiecewiseBezier([geometry])
    if isinstance(geometry, PiecewiseBezier):
        for subpath in geometry.subpaths:
            vertices.append(subpath.segments[0].p0.coords)
            codes.append(Path.MOVETO)
            for segment in subpath.segments:
                vertices.extend(point.coords for point in segment.control_points[1:])
                codes.extend([Path.CURVE4] * 3)
            if closed or subpath.closed:
                vertices.append(subpath.segments[0].p0.coords)
                codes.append(Path.CLOSEPOLY)
    else:
        vertices = [point.coords for point in geometry]
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
