"""Axis marks, notes, and braces: measured, placed, then drawn after every builder.

Inside brace labels are placed last so they avoid everything already on the axes,
the braces and gutter texts included.
"""

from collections.abc import Sequence
from typing import Any

from mosaickit.errors import RenderError
from mosaickit.rendering.matplotlib.fonts import measure_text
from mosaickit.rendering.matplotlib.gutter.draw import draw_brace, draw_inside_label, draw_text
from mosaickit.rendering.matplotlib.gutter.frame import AxisFrame
from mosaickit.rendering.matplotlib.gutter.place import Item, plan_gutter
from mosaickit.rendering.matplotlib.gutter.text import as_drawn
from mosaickit.rendering.matplotlib.obstacles import collect_obstacles
from mosaickit.rendering.matplotlib.registry import PassContext
from mosaickit.scene import AxisMarkLayer, AxisNoteLayer, BraceLayer
from mosaickit.scene.axis_layer import AXES

_TEXT_FIELD = {AxisMarkLayer: "label", AxisNoteLayer: "text", BraceLayer: "label"}


def _item(ax: Any, resolved: Any, renderer: Any) -> Item:
    layer = resolved.layer
    field = _TEXT_FIELD.get(type(layer))
    if field is None:
        raise RenderError(f"No gutter layout for {type(layer).__name__}")
    raw = getattr(layer, field)
    if raw is None:
        return Item(resolved, None, (0.0, 0.0))
    text = as_drawn(raw, getattr(layer, "math", False))
    return Item(resolved, text, measure_text(ax, text, resolved.style.text, renderer))


def gutter_pass(ax: Any, layers: Sequence[Any], context: PassContext) -> None:
    renderer = ax.figure.canvas.get_renderer()
    scale = ax.figure.dpi / 72
    inside_labels = []
    for axis in AXES:
        items = [_item(ax, r, renderer) for r in layers if r.layer.axis == axis]
        if not items:
            continue
        frame = AxisFrame.of(ax, axis)
        by_type = {
            kind: [i for i in items if type(i.resolved.layer) is kind] for kind in _TEXT_FIELD
        }
        plan = plan_gutter(
            ax, frame, by_type[AxisMarkLayer], by_type[BraceLayer], by_type[AxisNoteLayer], scale
        )
        for placed in plan.braces:
            draw_brace(ax, placed)
        for text in plan.texts:
            draw_text(ax, frame, text)
        sizes = {i.resolved.layer.id: i for i in by_type[BraceLayer]}
        inside_labels += [(frame, p, sizes[p.resolved.layer.id]) for p in plan.inside]
    obstacles = collect_obstacles(ax, renderer)
    for frame, placed, item in inside_labels:
        if item.text:
            obstacles = draw_inside_label(
                ax, frame, placed, item.text, item.size, obstacles, renderer
            )


__all__ = ["gutter_pass"]
