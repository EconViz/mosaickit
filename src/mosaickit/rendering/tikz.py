"""Pure TikZ export for backend-neutral MosaicKit scenes."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from mosaickit.canvas.canvas import Canvas
from mosaickit.canvas.grid import CanvasGrid
from mosaickit.colors import Color
from mosaickit.rendering.plan import _build_render_plan, _resolve_role
from mosaickit.scene import FillLayer, Layer, LegendLayer, MarkerLayer, PathLayer, TextLayer
from mosaickit.scene.text import TEXT_ANCHORS
from mosaickit.styles import ArrowPlacement, Stroke

PathSerializer = Callable[[Any, str], str]
_PATH_SERIALIZERS: dict[type, PathSerializer] = {}

_DASH = {"solid": "", "dashed": "dashed", "dotted": "dotted", "dashdot": "dash dot"}
_HORIZONTAL = {"left": "west", "right": "east", "center": ""}
_VERTICAL = {"top": "north", "bottom": "south", "center": ""}
_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
}
_ARROW_TIPS = {
    "open": "Latex[open,length=5pt]",
    "triangle": "Triangle[length=5pt]",
    "fancy": "Stealth[length=5pt]",
    "wedge": "Kite[length=5pt]",
}
_GENERIC_FONT_COMMANDS = {
    "sans": r"\sffamily",
    "serif": r"\rmfamily",
    "mono": r"\ttfamily",
}


def register_path_serializer(
    model_type: type, serializer: PathSerializer, *, replace: bool = False
) -> None:
    """Register TikZ serialization for a model attached to a :class:`PathLayer`."""
    if model_type in _PATH_SERIALIZERS and not replace:
        raise ValueError(f"TikZ path serializer already registered for {model_type.__name__}")
    _PATH_SERIALIZERS[model_type] = serializer


def _serializer_for(model: Any) -> PathSerializer | None:
    if model is None:
        return None
    for model_type in type(model).__mro__:
        if model_type in _PATH_SERIALIZERS:
            return _PATH_SERIALIZERS[model_type]
    return None


class _Colors:
    def __init__(self, palette) -> None:
        self._palette = palette
        self.defined: dict[str, str] = {}

    def name(self, color: Color | str) -> str:
        if isinstance(color, str):
            color = Color.from_hex(color) if color.startswith("#") else self._palette[color]
        value = color.to_hex(include_alpha=False).lstrip("#").upper()
        name = f"mk{value}"
        self.defined[name] = value
        return name


def _number(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


def _points(points: object) -> str:
    return " -- ".join(
        f"({_number(x)},{_number(y)})"
        for x, y in points  # type: ignore[attr-defined]
    )


def _stroke_options(stroke: Stroke, placement: ArrowPlacement, colors: _Colors) -> list[str]:
    opts = [colors.name(stroke.color), f"line width={_number(stroke.width)}pt"]  # type: ignore[arg-type]
    dash = _DASH[stroke.dash.value]  # type: ignore[union-attr]
    if dash:
        opts.append(dash)
    if stroke.opacity is not None and stroke.opacity < 1:
        opts.append(f"opacity={_number(stroke.opacity)}")
    if stroke.arrow is not None:
        tip = "{" + _ARROW_TIPS[stroke.arrow.value] + "}"
        opts.append(
            {
                ArrowPlacement.END: f"-{tip}",
                ArrowPlacement.START: f"{tip}-",
                ArrowPlacement.BOTH: f"{tip}-{tip}",
            }[placement]
        )
    return opts


def _path_command(layer: PathLayer, bundle: Any, colors: _Colors, clip: str) -> str:
    stroke = bundle.stroke
    assert stroke is not None
    opts = _stroke_options(stroke, layer.arrow_placement, colors)
    serializer = _serializer_for(layer.model)
    command = (
        serializer(layer.model, ",".join(opts))
        if serializer is not None
        else f"\\draw[{','.join(opts)}] {_points(layer.path)};"
    )
    return f"\\begin{{scope}}{clip}{command}\\end{{scope}}" if layer.clip else command


def _fill_command(layer: FillLayer, bundle: Any, colors: _Colors) -> str:
    fill = bundle.fill
    assert fill is not None
    opts = [colors.name(fill.color)]  # type: ignore[arg-type]
    if fill.opacity is not None and fill.opacity < 1:
        opts.append(f"opacity={_number(fill.opacity)}")
    return f"\\fill[{','.join(opts)}] {_points(layer.boundary)} -- cycle;"


def _marker_command(x: float, y: float, radius: float, shape: str, opts: list[str]) -> str:
    coordinate = f"{_number(x)},{_number(y)}"
    style = ",".join(opts)

    def shifted(dx: float, dy: float) -> str:
        return f"([xshift={_number(dx)}pt,yshift={_number(dy)}pt]{coordinate})"

    def polygon(vertices: list[tuple[float, float]]) -> str:
        points = " -- ".join(shifted(dx * radius, dy * radius) for dx, dy in vertices)
        return f"\\fill[{style}] {points} -- cycle;"

    if shape in {"s", "square"}:
        return f"\\fill[{style}] {shifted(-radius, -radius)} rectangle {shifted(radius, radius)};"
    if shape in {"D", "d", "diamond"}:
        width = 0.65 if shape == "d" else 1
        return polygon([(0, 1), (width, 0), (0, -1), (-width, 0)])
    if shape in {"^", "v", "<", ">"}:
        vertices = {
            "^": ((0, 1), (1, -1), (-1, -1)),
            "v": ((0, -1), (1, 1), (-1, 1)),
            "<": ((-1, 0), (1, 1), (1, -1)),
            ">": ((1, 0), (-1, 1), (-1, -1)),
        }[shape]
        return polygon(list(vertices))
    if shape == "*":
        star_vertices: list[tuple[float, float]] = []
        for index in range(10):
            angle = math.pi / 2 + index * math.pi / 5
            length = 1 if index % 2 == 0 else 0.4
            star_vertices.append((math.cos(angle) * length, math.sin(angle) * length))
        return polygon(star_vertices)
    if shape in {"p", "h", "H"}:
        sides = 5 if shape == "p" else 6
        rotation = math.pi / 2 if shape != "H" else 0
        return polygon(
            [
                (
                    math.cos(rotation + index * 2 * math.pi / sides),
                    math.sin(rotation + index * 2 * math.pi / sides),
                )
                for index in range(sides)
            ]
        )
    if shape in {"+", "x", "|", "_"}:
        segments = {
            "+": [((-1, 0), (1, 0)), ((0, -1), (0, 1))],
            "x": [((-1, -1), (1, 1)), ((-1, 1), (1, -1))],
            "|": [((0, -1), (0, 1))],
            "_": [((-1, 0), (1, 0))],
        }[shape]
        return " ".join(
            f"\\draw[{style},line width={_number(max(radius / 2, 0.5))}pt] "
            f"{shifted(a[0] * radius, a[1] * radius)} -- {shifted(b[0] * radius, b[1] * radius)};"
            for a, b in segments
        )
    r = radius * 0.3 if shape in {".", ","} else radius
    return f"\\fill[{style}] ({coordinate}) circle ({_number(r)}pt);"


def _marker_commands(layer: MarkerLayer, bundle: Any, colors: _Colors) -> list[str]:
    marker = bundle.marker
    assert marker is not None
    radius = math.sqrt(marker.size) / 2  # type: ignore[arg-type]
    opts = [colors.name(marker.color)]  # type: ignore[arg-type]
    if marker.opacity is not None and marker.opacity < 1:
        opts.append(f"opacity={_number(marker.opacity)}")
    return [_marker_command(x, y, radius, marker.shape or "o", opts) for x, y in layer.points]


def _text_command(layer: TextLayer, bundle: Any, colors: _Colors) -> str:
    style = bundle.text
    assert style is not None
    horizontal, vertical = TEXT_ANCHORS[layer.anchor]
    anchor = " ".join(part for part in (_VERTICAL[vertical], _HORIZONTAL[horizontal]) if part)
    size = float(style.size or 12)
    font = f"\\fontsize{{{_number(size)}}}{{{_number(size * 1.2)}}}\\selectfont"
    family = _GENERIC_FONT_COMMANDS.get(style.font or "")
    if family:
        font += family
    opts = [
        f"text={colors.name(style.color)}",  # type: ignore[arg-type]
        f"font={{{font}}}",
        f"xshift={_number(layer.total_offset[0])}pt",
        f"yshift={_number(layer.total_offset[1])}pt",
    ]
    if style.opacity is not None and style.opacity < 1:
        opts.append(f"text opacity={_number(style.opacity)}")
    if anchor:
        opts.insert(0, f"anchor={anchor}")
    raw = str(layer.text)
    already_math = len(raw) >= 2 and raw.startswith("$") and raw.endswith("$")
    text = (
        raw
        if already_math
        else f"${raw}$"
        if layer.math
        else "".join(_ESCAPES.get(c, c) for c in raw)
    )
    x, y = layer.position
    return f"\\node[{','.join(opts)}] at ({_number(x)},{_number(y)}) {{{text}}};"


def _background_command(canvas: Canvas, colors: _Colors) -> str | None:
    fill = _resolve_role(canvas._context(), "canvas", "fill").fill
    if fill is None or fill.opacity == 0:
        return None
    spec = canvas.spec
    opts = [f"fill={colors.name(fill.color)}"]  # type: ignore[arg-type]
    if fill.opacity is not None and fill.opacity < 1:
        opts.append(f"fill opacity={_number(fill.opacity)}")
    return (
        f"\\path[{','.join(opts)}] ({_number(spec.x_min)},{_number(spec.y_min)}) rectangle "
        f"({_number(spec.x_max)},{_number(spec.y_max)});"
    )


def _legend_command(
    layer: LegendLayer, entries: tuple[str, ...], bundle: Any, canvas: Canvas, colors: _Colors
) -> str | None:
    style = bundle.legend
    if style is None or style.visible is False or not entries:
        return None
    spec = canvas.spec
    positions = {
        "best": ((spec.x_max, spec.y_max), "north east"),
        "upper right": ((spec.x_max, spec.y_max), "north east"),
        "upper left": ((spec.x_min, spec.y_max), "north west"),
        "lower left": ((spec.x_min, spec.y_min), "south west"),
        "lower right": ((spec.x_max, spec.y_min), "south east"),
        "upper center": (((spec.x_min + spec.x_max) / 2, spec.y_max), "south"),
        "lower center": (((spec.x_min + spec.x_max) / 2, spec.y_min), "north"),
        "center left": ((spec.x_min, (spec.y_min + spec.y_max) / 2), "east"),
        "center right": ((spec.x_max, (spec.y_min + spec.y_max) / 2), "west"),
        "top": (((spec.x_min + spec.x_max) / 2, spec.y_max), "south"),
        "bottom": (((spec.x_min + spec.x_max) / 2, spec.y_min), "north"),
        "left": ((spec.x_min, (spec.y_min + spec.y_max) / 2), "east"),
        "right": ((spec.x_max, (spec.y_min + spec.y_max) / 2), "west"),
    }
    position, anchor = positions.get(style.location or "best", positions["best"])
    opts = [f"anchor={anchor}", "align=left", "inner sep=3pt"]
    if style.frame:
        opts.append("draw")
    text_style = bundle.text
    if text_style is not None and text_style.color is not None:
        opts.append(f"text={colors.name(text_style.color)}")
    size = float(style.size or (text_style.size if text_style else 10) or 10)
    opts.append(f"font={{\\fontsize{{{_number(size)}}}{{{_number(size * 1.2)}}}\\selectfont}}")
    content = r" \\ ".join("".join(_ESCAPES.get(c, c) for c in item) for item in entries)
    return (
        f"\\node[{','.join(opts)}] at "
        f"({_number(position[0])},{_number(position[1])}) {{{content}}};"
    )


def _layer_commands(layer: Layer, bundle: Any, colors: _Colors, clip: str) -> list[str]:
    if isinstance(layer, PathLayer):
        return [_path_command(layer, bundle, colors, clip)]
    if isinstance(layer, FillLayer):
        return [_fill_command(layer, bundle, colors)]
    if isinstance(layer, MarkerLayer):
        return _marker_commands(layer, bundle, colors)
    if isinstance(layer, TextLayer):
        return [_text_command(layer, bundle, colors)]
    if isinstance(layer, LegendLayer):
        return []
    raise NotImplementedError(f"TikZ export does not support {type(layer).__name__}")


def canvas_to_tikz(canvas: Canvas, *, standalone: bool = True) -> str:
    """Return a TikZ picture or standalone document for ``canvas``."""
    spec = canvas.spec
    colors = _Colors(canvas.config.palette)
    x0, x1, y0, y1 = spec.x_min, spec.x_max, spec.y_min, spec.y_max
    clip = f"\\clip ({_number(x0)},{_number(y0)}) rectangle ({_number(x1)},{_number(y1)});"
    background = _background_command(canvas, colors)
    body: list[str] = [background] if background else []
    layers = _build_render_plan(canvas.snapshot(), canvas._context()).layers
    legend_entries = tuple(dict.fromkeys(item.layer.legend for item in layers if item.layer.legend))
    for item in layers:
        layer, bundle = item.layer, item.style
        if isinstance(layer, LegendLayer):
            command = _legend_command(
                layer, layer.entries or legend_entries, bundle, canvas, colors
            )
            if command:
                body.append(command)
        else:
            body.extend(_layer_commands(layer, bundle, colors, clip))
    definitions = "\n".join(
        f"\\definecolor{{{name}}}{{HTML}}{{{value}}}"
        for name, value in sorted(colors.defined.items())
    )
    picture = (
        f"\\begin{{tikzpicture}}[x={_number(spec.width / (x1 - x0))}in,"
        f"y={_number(spec.height / (y1 - y0))}in]\n" + "\n".join(body) + "\n\\end{tikzpicture}\n"
    )
    if not standalone:
        return f"{definitions}\n{picture}"
    return (
        "\\documentclass[tikz,border=12pt]{standalone}\n"
        "\\usepackage{xcolor}\n\\usetikzlibrary{arrows.meta}\n"
        f"{definitions}\n\\begin{{document}}\n{picture}\\end{{document}}\n"
    )


def grid_to_tikz(grid: CanvasGrid, *, standalone: bool = True) -> str:
    """Return a laid-out TikZ document for a :class:`CanvasGrid`."""
    definitions: set[str] = set()
    pictures: dict[tuple[int, int], str] = {}
    for placement in grid.placements:
        source = canvas_to_tikz(placement.canvas, standalone=False)
        picture_at = source.index(r"\begin{tikzpicture}")
        definitions.update(line for line in source[:picture_at].splitlines() if line)
        pictures[(placement.row, placement.col)] = source[picture_at:]

    spacing = grid.spacing
    custom_outer = spacing.outer is not None
    unit_width = max(
        (placement.canvas.spec.width / placement.cols for placement in grid.placements), default=6
    )
    unit_height = max(
        (placement.canvas.spec.height / placement.rows for placement in grid.placements), default=6
    )
    column_separator = (
        rf"\hspace{{{_number(spacing.column_gap * unit_width)}in}}"
        if spacing.column_gap is not None
        else r"\hspace{1em}"
    )
    row_separator = (
        rf"\par\vspace{{{_number(spacing.row_gap * unit_height)}in}}"
        if spacing.row_gap is not None
        else r"\par\medskip"
    )
    outer_x = (spacing.outer or 0) * unit_width * grid.cols
    outer_y = (spacing.outer or 0) * unit_height * grid.rows
    lines = [r"\begin{center}" if not custom_outer else rf"\vspace*{{{_number(outer_y)}in}}"]
    for row in range(grid.rows):
        row_pictures = [
            pictures[(placement.row, placement.col)]
            for placement in grid.placements
            if placement.row == row
        ]
        if not row_pictures:
            continue
        lines.append(f"% row {row + 1} of {grid.rows}")
        row_body = column_separator.join(row_pictures)
        if custom_outer:
            row_body = (
                rf"\noindent\hspace*{{{_number(outer_x)}in}}"
                + row_body
                + rf"\hspace*{{{_number(outer_x)}in}}"
            )
        lines.append(row_body)
        if any(placement.row > row for placement in grid.placements):
            lines.append(row_separator)
    lines.append(r"\end{center}" if not custom_outer else rf"\vspace*{{{_number(outer_y)}in}}")
    body = "\n".join(sorted(definitions)) + "\n" + "\n".join(lines)
    if not standalone:
        return body
    return (
        "\\documentclass[tikz,border=12pt]{standalone}\n"
        "\\usepackage{xcolor}\n\\usetikzlibrary{arrows.meta}\n"
        f"\\begin{{document}}\n{body}\n\\end{{document}}\n"
    )


__all__ = ["canvas_to_tikz", "grid_to_tikz", "register_path_serializer"]
