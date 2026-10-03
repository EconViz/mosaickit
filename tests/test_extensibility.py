"""A new layer type plugs in without touching the render plan or the renderer."""

from dataclasses import dataclass, field
from typing import Any, ClassVar

from matplotlib.lines import Line2D

from mosaickit import Canvas, FillLayer, Layer, RegionLabelLayer, Stroke, TextStyle
from mosaickit.layout.geometry import Rect, rect_hits_segment
from mosaickit.rendering.matplotlib import register_builder
from mosaickit.rendering.plan import _build_render_plan


@dataclass(frozen=True, slots=True)
class Caption(Layer):
    """Text whose style lives in a field not named ``style``."""

    role: str = field(default="text", kw_only=True)
    font: TextStyle | None = None
    style_slots: ClassVar[dict[str, str]] = {"text": "font"}
    fallback_category: ClassVar[str] = "text"


@dataclass(frozen=True, slots=True)
class Wall(Layer):
    """A vertical line drawn by a custom builder."""

    x: float = 0.0
    pen: Stroke | None = None
    style_slots: ClassVar[dict[str, str]] = {"stroke": "pen"}


def _draw_wall(ax: Any, resolved: Any) -> Any:
    stroke = resolved.style.stroke
    line = Line2D([resolved.layer.x] * 2, [0, 10], linewidth=stroke.width, color="black")
    ax.add_line(line)
    return line


register_builder(Wall, _draw_wall)


def test_plan_reads_explicit_styles_from_declared_slots():
    canvas = Canvas().add(Caption(font=TextStyle(size=31), id="c"))
    (resolved,) = _build_render_plan(canvas.snapshot(), canvas._context()).layers
    assert resolved.style.text.size == 31


def test_registered_layer_type_renders_and_resolves_its_stroke():
    result = Canvas().add(Wall(x=4, pen=Stroke(width=7), id="w")).render()
    try:
        (line,) = [a for a in result.axes.lines if a.get_gid() == "w"]
        assert line.get_linewidth() == 7
    finally:
        result.close()


def test_callouts_avoid_whatever_was_drawn_even_by_unknown_layer_types():
    small = [(5, 5), (5.3, 5), (5, 5.3)]
    result = (
        Canvas()
        .add(FillLayer(small, id="s"))
        .add(Wall(x=6.0, pen=Stroke(width=1), id="w"))
        .add(RegionLabelLayer("s", "Small region label", id="s.label"))
        .render()
    )
    try:
        ax = result.axes
        renderer = ax.figure.canvas.get_renderer()
        label = next(t for t in ax.texts if t.get_gid() == "s.label")
        box = label.get_window_extent(renderer)
        a, b = ax.transData.transform([(6.0, 0), (6.0, 10)])
        assert not rect_hits_segment(Rect(box.x0, box.y0, box.x1, box.y1), tuple(a), tuple(b))
    finally:
        result.close()
