"""Deterministic legend placement and style samples."""

from dataclasses import replace

from bezierkit import Point

from mosaickit.errors import RenderError
from mosaickit.rendering.tikz.document import escape_text
from mosaickit.rendering.tikz.options.stroke_options import color_option, translate
from mosaickit.scene import FillLayer, MarkerLayer


def legend_commands(layer, style, labelled, context, coordinate):
    ids = layer.entries or tuple(labelled)
    if not ids:
        return []
    missing = set(ids) - labelled.keys()
    if missing:
        raise RenderError(f"Legend references missing or unlabelled layers: {sorted(missing)}")
    location = "upper right" if style.location == "best" else style.location
    anchors = {
        "upper right": "north east",
        "upper left": "north west",
        "lower right": "south east",
        "lower left": "south west",
        "upper center": "north",
        "lower center": "south",
        "center": "center",
        "center left": "west",
        "center right": "east",
        "right": "east",
    }
    if location not in anchors:
        raise RenderError(f"Unsupported TikZ legend location: {location!r}")
    spec = context.spec
    x = (
        spec.x_min
        if "left" in location
        else spec.x_max
        if "right" in location
        else (spec.x_min + spec.x_max) / 2
    )
    y = (
        spec.y_max
        if "upper" in location
        else spec.y_min
        if "lower" in location
        else (spec.y_min + spec.y_max) / 2
    )
    rows = []
    for key in ids:
        entry = labelled[key]
        if isinstance(entry.layer, MarkerLayer):
            color = color_option(entry.style.marker.color)
            sample = f"\\fill[fill={color}] (0,0) circle[radius=2pt];"
        elif isinstance(entry.layer, FillLayer):
            color = color_option(entry.style.fill.color)
            sample = f"\\fill[fill={color}] (0,-0.07) rectangle (0.35,0.07);"
        else:
            opts = translate(replace(entry.style.stroke, arrow=None))
            sample = f"\\draw[{opts}] (0,0) -- (0.35,0);"
        label = escape_text(entry.layer.legend)
        rows.append(f"\\tikz[baseline=-0.5ex]{{{sample}}} & {label} \\\\")
    frame = "draw," if style.frame else ""
    font = f"\\fontsize{{{style.size:g}}}{{{style.size * 1.2:g}}}\\selectfont"
    table = "\n".join(rows)
    return [
        f"\\node[{frame}anchor={anchors[location]},font={{{font}}}] "
        f"at {coordinate(Point(x, y))} {{\\begin{{tabular}}{{ll}}\n{table}\n\\end{{tabular}}}};"
    ]
