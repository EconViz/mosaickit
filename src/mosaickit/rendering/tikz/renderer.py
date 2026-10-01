"""Style translation and document assembly on BezierKit's public exporter."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from bezierkit import CubicBezierSegment, PiecewiseBezier, Point
from bezierkit.export.tikz import to_tikz

from mosaickit.errors import ConfigurationError, RenderError
from mosaickit.rendering.plan import _build_render_plan, _resolve_role
from mosaickit.rendering.protocol import SaveOptions
from mosaickit.rendering.tikz.document import assemble, escape_text
from mosaickit.rendering.tikz.legend import legend_commands
from mosaickit.rendering.tikz.options import fill_options, stroke_options, text_options
from mosaickit.scene import (
    ArrowLayer,
    FillLayer,
    LegendLayer,
    MarkerLayer,
    PathLayer,
    TextLayer,
)
from mosaickit.styles import ArrowStyle


@dataclass(frozen=True, slots=True)
class TikzOptions:
    mode: Literal["inline", "separate"] = "inline"

    def __post_init__(self) -> None:
        if self.mode not in ("inline", "separate"):
            raise ConfigurationError(f"Unknown TikZ mode: {self.mode!r}")


@dataclass(frozen=True, slots=True)
class TikzResult:
    plans: tuple
    contexts: tuple
    placements: tuple = ()


def _path(geometry, closed=False):
    if isinstance(geometry, PiecewiseBezier):
        if closed and not all(subpath.closed for subpath in geometry.subpaths):
            paths = []
            for subpath in geometry.subpaths:
                segments = list(subpath.segments)
                if segments[-1].p3 != segments[0].p0:
                    segments.append(CubicBezierSegment.from_line(segments[-1].p3, segments[0].p0))
                paths.append(PiecewiseBezier(segments, closed=True))
            return PiecewiseBezier.compound(paths)
        return geometry
    if isinstance(geometry, CubicBezierSegment):
        return _path(PiecewiseBezier([geometry]), closed)
    points = list(geometry)
    if closed and points[0] != points[-1]:
        points.append(points[0])
    return PiecewiseBezier(
        [CubicBezierSegment.from_line(a, b) for a, b in zip(points, points[1:], strict=False)],
        closed=closed,
    )


class TikzRenderer:
    name = "tikz"

    def __init__(self, options: TikzOptions | None = None) -> None:
        self.options = options or TikzOptions()

    def render(self, scene, context) -> TikzResult:
        return TikzResult((_build_render_plan(scene, context),), (context,))

    def render_grid(self, grid, cache) -> TikzResult:
        contexts = tuple(p.canvas._context(cache) for p in grid.placements)
        plans = tuple(
            _build_render_plan(p.canvas.snapshot(), context)
            for p, context in zip(grid.placements, contexts, strict=True)
        )
        return TikzResult(plans, contexts, grid.placements)

    def _body(self, plan, context, options) -> str:
        scale = options.tikz_scale

        def transform(point):
            return Point(point.x * scale, point.y * scale)

        def coordinate(point):
            return (
                f"({point.x * scale:.{options.precision}f},{point.y * scale:.{options.precision}f})"
            )

        commands = []
        if context.spec.title:
            title_style = _resolve_role(context, "title", "text").text
            position = Point((context.spec.x_min + context.spec.x_max) / 2, context.spec.y_max)
            commands.append(
                f"\\node[{text_options.translate(title_style)},anchor=south,yshift=6pt] "
                f"at {coordinate(position)} {{{escape_text(context.spec.title)}}};"
            )
        labelled = {item.layer.id: item for item in plan.layers if item.layer.legend}
        for item in plan.layers:
            layer, style = item.layer, item.style
            if isinstance(layer, (PathLayer, FillLayer, ArrowLayer)):
                stroke = style.stroke
                if isinstance(layer, ArrowLayer):
                    geometry = _path((layer.start, layer.end))
                    if stroke.arrow is None:
                        stroke = replace(stroke, arrow=ArrowStyle.OPEN)
                else:
                    geometry = _path(
                        layer.boundary if isinstance(layer, FillLayer) else layer.path,
                        isinstance(layer, FillLayer),
                    )
                opts = stroke_options.translate(stroke, getattr(layer, "arrow_placement", "end"))
                if isinstance(layer, FillLayer):
                    opts += "," + fill_options.translate(style.fill)
                if isinstance(layer, FillLayer):
                    serialized = to_tikz(geometry, precision=options.precision, transform=transform)
                    subpaths = " ".join(
                        line.removeprefix("\\draw ").removesuffix(";")
                        for line in serialized.splitlines()
                    )
                    commands.append(f"\\path[{opts}] {subpaths};")
                else:
                    commands.append(
                        to_tikz(
                            geometry, options=opts, precision=options.precision, transform=transform
                        )
                    )
                if isinstance(layer, ArrowLayer) and layer.label:
                    middle = Point(
                        (layer.start.x + layer.end.x) / 2, (layer.start.y + layer.end.y) / 2
                    )
                    commands.append(
                        f"\\node at {coordinate(middle)} {{{escape_text(layer.label)}}};"
                    )
            elif isinstance(layer, TextLayer):
                label = str(layer.text)
                label = f"${label.strip('$')}$" if layer.math else escape_text(label)
                anchors = {
                    "center": "center",
                    "left": "west",
                    "right": "east",
                    "top": "north",
                    "bottom": "south",
                }
                opts = (
                    f"{text_options.translate(style.text)},anchor={anchors[layer.anchor]},"
                    f"xshift={layer.offset[0]:g}pt,yshift={layer.offset[1]:g}pt"
                )
                commands.append(f"\\node[{opts}] at {coordinate(layer.position)} {{{label}}};")
            elif isinstance(layer, MarkerLayer):
                marker = style.marker
                shapes = {
                    "o": "*",
                    "s": "square*",
                    "^": "triangle*",
                    "+": "+",
                    "x": "x",
                    "D": "diamond*",
                }
                if marker.shape not in shapes:
                    raise RenderError(f"Unsupported TikZ marker: {marker.shape!r}")
                points = " ".join(coordinate(point) for point in layer.points)
                color = stroke_options.color_option(marker.color)
                edge = stroke_options.color_option(marker.edge_color)
                commands.append(
                    f"\\path plot[only marks,mark={shapes[marker.shape]},"
                    f"mark size={marker.size**0.5 / 2:g}pt,mark options={{fill={color},"
                    f"fill opacity={marker.opacity * marker.color.alpha:g},draw={edge},"
                    f"draw opacity={marker.opacity * marker.edge_color.alpha:g},"
                    f"line width={marker.edge_width:g}pt}}] coordinates {{{points}}};"
                )
            elif isinstance(layer, LegendLayer):
                if not style.legend.visible:
                    continue
                commands.extend(legend_commands(layer, style.legend, labelled, context, coordinate))
            else:
                raise RenderError(f"Unsupported TikZ layer: {type(layer).__name__}")
        return "\n".join(commands)

    def save(self, result: TikzResult, target: Path, options: SaveOptions) -> list[Path]:
        if target.suffix.lower() not in {".tex", ".pgf"}:
            raise RenderError(f"TikZ does not support {target.suffix!r}")
        if self.options.mode == "separate" or options.mode == "separate":
            raise NotImplementedError(
                "Separate TikZ output requires BezierKit.export.tikz.to_tikz_separate"
            )
        bodies = []
        if result.placements:
            unit_x = max(
                (context.spec.x_max - context.spec.x_min) / p.cols
                for p, context in zip(result.placements, result.contexts, strict=True)
            )
            unit_y = max(
                (context.spec.y_max - context.spec.y_min) / p.rows
                for p, context in zip(result.placements, result.contexts, strict=True)
            )
        for index, (plan, context) in enumerate(zip(result.plans, result.contexts, strict=True)):
            body = self._body(plan, context, options)
            if result.placements:
                p = result.placements[index]
                sx = (unit_x * p.cols + 2 * (p.cols - 1)) / (
                    context.spec.x_max - context.spec.x_min
                )
                sy = (unit_y * p.rows + 2 * (p.rows - 1)) / (
                    context.spec.y_max - context.spec.y_min
                )
                x = (p.col * (unit_x + 2) - sx * context.spec.x_min) * options.tikz_scale
                y = (-p.row * (unit_y + 2) - sy * context.spec.y_max) * options.tikz_scale
                body = (
                    f"\\begin{{scope}}[shift={{({x:g},{y:g})}},xscale={sx:g},yscale={sy:g}]\n"
                    f"{body}\n\\end{{scope}}"
                )
            bodies.append(body)
        target.write_text(assemble("\n".join(bodies), fragment=options.fragment), encoding="utf-8")
        return [target]
