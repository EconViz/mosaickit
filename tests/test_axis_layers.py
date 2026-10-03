import pytest

from mosaickit import (
    AxisMarkLayer,
    AxisNoteLayer,
    BraceLayer,
    Canvas,
    ConfigurationError,
    Parameter,
    Stroke,
    TextStyle,
)
from mosaickit.rendering.plan import _build_render_plan


def test_mark_note_and_brace_hold_their_fields():
    mark = AxisMarkLayer("y", 5, "a_1", math=True)
    note = AxisNoteLayer("x", 2.5, "Upper\nvalue")
    brace = BraceLayer("y", 4, 7, "Span", side="outside")
    assert (mark.axis, mark.value, mark.label, mark.math) == ("y", 5.0, "a_1", True)
    assert (note.axis, note.value, note.text) == ("x", 2.5, "Upper\nvalue")
    assert (brace.start, brace.end, brace.label, brace.side) == (4.0, 7.0, "Span", "outside")
    assert BraceLayer("y", 1, 2).side == "inside"


@pytest.mark.parametrize(
    "build",
    [
        lambda: AxisMarkLayer("z", 1, "a"),
        lambda: AxisMarkLayer("y", float("nan"), "a"),
        lambda: AxisMarkLayer("y", 1, ""),
        lambda: AxisNoteLayer("y", 1, ""),
        lambda: AxisNoteLayer("y", "1", "text"),
        lambda: BraceLayer("y", 1, 1),
        lambda: BraceLayer("y", 1, 2, side="middle"),
        lambda: BraceLayer("y", 1, 2, label=""),
    ],
)
def test_invalid_values_are_rejected(build):
    with pytest.raises(ConfigurationError):
        build()


def test_layers_declare_style_slots_and_default_roles():
    assert AxisMarkLayer.style_slots == {"text": "style"}
    assert AxisNoteLayer.style_slots == {"text": "style"}
    assert BraceLayer.style_slots == {"stroke": "stroke", "text": "style"}
    assert AxisMarkLayer("y", 1, "a").role == "axes"
    assert AxisNoteLayer("y", 1, "a").role == "axes.note"
    assert BraceLayer("y", 1, 2).role == "axes"


def test_explicit_styles_flow_through_the_plan():
    canvas = Canvas().add(
        BraceLayer("y", 1, 2, "Span", stroke=Stroke(width=3), style=TextStyle(size=20), id="brace")
    )
    plan = _build_render_plan(canvas.snapshot(), canvas._context())
    resolved = next(r for r in plan.layers if r.layer.id == "brace")
    assert resolved.style.stroke.width == 3
    assert resolved.style.text.size == 20


def test_notes_default_to_a_smaller_quieter_text_style():
    canvas = (
        Canvas().add(AxisNoteLayer("y", 1, "note", id="n")).add(AxisMarkLayer("y", 1, "a", id="m"))
    )
    plan = _build_render_plan(canvas.snapshot(), canvas._context())
    styles = {r.layer.id: r.style.text for r in plan.layers}
    assert styles["n"].size < styles["m"].size
    assert styles["n"].color != styles["m"].color


def test_values_accept_parameters():
    value = Parameter("value", value_type=float)
    canvas = Canvas().add(AxisMarkLayer("y", value, "a", id="m"))
    bound = canvas.bind(value, 3.0).snapshot()
    assert bound.layers[0].value == 3.0
