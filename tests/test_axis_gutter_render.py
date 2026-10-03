import itertools

import pytest

from mosaickit import (
    AxisMarkLayer,
    AxisNoteLayer,
    AxisSpec,
    BraceLayer,
    Canvas,
    CanvasSpec,
    PathLayer,
    build_axes,
    quadrant_axes,
)
from mosaickit.layout.geometry import Rect, rect_hits_segment
from mosaickit.styles import ArrowPlacement

MARKS = [(7.0, "a_1", "Upper\nvalue"), (5.6, "a_0", "Middle\nvalue"), (5.0, "a_2", "Lower\nvalue")]
LINES = [[(0, 9), (10, 1)], [(0, 2), (10, 9)], [(0, 4.5), (10, 9.5)]]


def _canvas(side="inside", axis="y", notes=True, brace=True):
    canvas = Canvas(CanvasSpec(width=6, height=5, dpi=100)).extend(quadrant_axes(10, 10))
    for i, line in enumerate(LINES):
        canvas.add(PathLayer(line, id=f"line{i}"))
    for value, label, note in MARKS:
        canvas.add(AxisMarkLayer(axis, value, label, math=True, id=f"mark.{label}"))
        if notes:
            canvas.add(AxisNoteLayer(axis, value, note, id=f"note.{label}"))
    if brace:
        canvas.add(BraceLayer(axis, 5.0, 7.0, "Span", side=side, id="brace"))
    return canvas


def _rect(ax, artist):
    box = artist.get_window_extent(ax.figure.canvas.get_renderer())
    return Rect(box.x0, box.y0, box.x1, box.y1)


def _texts(ax, prefix):
    return {t.get_gid(): t for t in ax.texts if (t.get_gid() or "").startswith(prefix)}


def _line(ax, gid):
    return next(line for line in ax.lines if line.get_gid() == gid)


def _overlap(a: Rect, b: Rect) -> bool:
    return a.x0 < b.x1 and b.x0 < a.x1 and a.y0 < b.y1 and b.y0 < a.y1


@pytest.mark.parametrize("side", ["inside", "outside"])
@pytest.mark.parametrize("axis", ["x", "y"])
def test_no_two_gutter_texts_overlap(side, axis):
    result = _canvas(side, axis).render()
    try:
        ax = result.axes
        texts = [t for t in ax.texts if t.get_gid()]
        assert len(texts) >= 7
        rects = [_rect(ax, t) for t in texts]
        for (a, ra), (b, rb) in itertools.combinations(zip(texts, rects, strict=True), 2):
            assert not _overlap(ra, rb), (a.get_text(), b.get_text())
    finally:
        result.close()


def test_y_columns_run_outward_marks_then_notes():
    result = _canvas(brace=False).render()
    try:
        ax = result.axes
        axis_x = ax.bbox.x0
        marks = [_rect(ax, t) for t in _texts(ax, "mark.").values()]
        notes = [_rect(ax, t) for t in _texts(ax, "note.").values()]
        assert all(r.x1 < axis_x for r in marks)
        assert max(r.x1 for r in notes) < min(r.x0 for r in marks)
    finally:
        result.close()


def test_uncrowded_mark_is_centred_on_its_value():
    canvas = Canvas(CanvasSpec(dpi=100)).extend(quadrant_axes(10, 10))
    canvas.add(AxisMarkLayer("y", 3, "a_1", math=True, id="m"))
    result = canvas.render()
    try:
        ax = result.axes
        rect = _rect(ax, _texts(ax, "m")["m"])
        assert rect.center[1] == pytest.approx(ax.transData.transform((0, 3))[1], abs=1)
    finally:
        result.close()


def test_crowded_marks_keep_their_order():
    result = _canvas(brace=False).render()
    try:
        ax = result.axes
        ys = [
            _rect(ax, _texts(ax, f"mark.{label}")[f"mark.{label}"]).center[1]
            for _, label, _ in MARKS
        ]
        assert ys == sorted(ys, reverse=True)
    finally:
        result.close()


def test_inside_brace_sits_in_the_plot_and_its_label_avoids_lines():
    result = _canvas("inside").render()
    try:
        ax = result.axes
        xs = _line(ax, "brace").get_xydata()
        display = ax.transData.transform(xs)
        assert display[:, 0].min() >= ax.bbox.x0
        lo, hi = ax.transData.transform([(0, 5), (0, 7)])[:, 1]
        assert display[:, 1].min() == pytest.approx(lo, abs=0.5)
        assert display[:, 1].max() == pytest.approx(hi, abs=0.5)
        label = _rect(ax, _texts(ax, "brace.label")["brace.label"])
        assert label.x0 > display[:, 0].max()
        for line in LINES:
            assert not rect_hits_segment(label, *map(tuple, ax.transData.transform(line)))
        assert label.within(Rect(*ax.bbox.extents))
    finally:
        result.close()


def test_outside_brace_sits_between_marks_and_notes():
    result = _canvas("outside").render()
    try:
        ax = result.axes
        display = ax.transData.transform(_line(ax, "brace").get_xydata())
        marks = [_rect(ax, t) for t in _texts(ax, "mark.").values()]
        notes = [_rect(ax, t) for t in _texts(ax, "note.").values()]
        label = _rect(ax, _texts(ax, "brace.label")["brace.label"])
        assert display[:, 0].max() < min(r.x0 for r in marks)
        assert label.x1 < display[:, 0].min()
        assert max(r.x1 for r in notes) < label.x0
    finally:
        result.close()


def test_x_axis_gutter_runs_downward():
    result = _canvas("outside", axis="x").render()
    try:
        ax = result.axes
        axis_y = ax.bbox.y0
        marks = [_rect(ax, t) for t in _texts(ax, "mark.").values()]
        notes = [_rect(ax, t) for t in _texts(ax, "note.").values()]
        display = ax.transData.transform(_line(ax, "brace").get_xydata())
        assert all(r.y1 < axis_y for r in marks)
        assert display[:, 1].max() < min(r.y0 for r in marks)
        assert max(r.y1 for r in notes) < display[:, 1].min()
    finally:
        result.close()


def test_x_axis_inside_brace_points_up_into_the_plot():
    result = _canvas("inside", axis="x", notes=False).render()
    try:
        ax = result.axes
        display = ax.transData.transform(_line(ax, "brace").get_xydata())
        assert display[:, 1].min() >= ax.bbox.y0
        label = _rect(ax, _texts(ax, "brace.label")["brace.label"])
        assert label.y0 > display[:, 1].max()
    finally:
        result.close()


def test_overlapping_outside_braces_use_separate_lanes():
    canvas = Canvas(CanvasSpec(dpi=100)).extend(quadrant_axes(10, 10))
    canvas.add(BraceLayer("y", 2, 6, "First", side="outside", id="b1"))
    canvas.add(BraceLayer("y", 4, 8, "Second", side="outside", id="b2"))
    result = canvas.render()
    try:
        ax = result.axes
        first = ax.transData.transform(_line(ax, "b1").get_xydata())
        second = ax.transData.transform(_line(ax, "b2").get_xydata())
        labels = [_rect(ax, t) for t in _texts(ax, "b").values()]
        assert second[:, 0].max() < first[:, 0].min() or first[:, 0].max() < second[:, 0].min()
        assert not _overlap(*labels)
    finally:
        result.close()


@pytest.mark.parametrize("arrow", [ArrowPlacement.END, ArrowPlacement.BOTH])
def test_axis_titles_sit_past_the_arrow_tips(arrow):
    layers = build_axes(
        AxisSpec((0, 10), arrow, label="Across"), AxisSpec((0, 10), arrow, label="Up")
    )
    result = Canvas(CanvasSpec(dpi=100)).extend(layers).render()
    try:
        ax = result.axes
        heads = [_rect(ax, patch) for patch in ax.patches]
        assert heads
        titles = {t.get_text(): _rect(ax, t) for t in ax.texts}
        for title in titles.values():
            assert not any(_overlap(title, head) for head in heads)
        tip_x, tip_y = ax.transData.transform((10, 10))
        assert titles["Across"].x0 > tip_x
        assert titles["Up"].y0 > tip_y
    finally:
        result.close()


def test_saved_image_expands_to_include_outside_text(tmp_path):
    from PIL import Image

    spec = CanvasSpec(width=4, height=3, dpi=50)
    plain = Canvas(spec).extend(quadrant_axes(10, 10))
    plain_path = tmp_path / "plain.png"
    plain.save(plain_path)
    assert Image.open(plain_path).size == (200, 150)

    wide = plain.copy().add(AxisNoteLayer("y", 5, "A long note that reaches far out", id="n"))
    wide_path = tmp_path / "wide.png"
    wide.save(wide_path)
    width, height = Image.open(wide_path).size
    assert width > 200 and height == 150

    result = wide.render()
    try:
        ax = result.axes
        note = _rect(ax, _texts(ax, "n")["n"])
        assert note.x0 < 0  # past the figure's left edge before saving
    finally:
        result.close()

    clipped = tmp_path / "clipped.png"
    wide.save(clipped, expand=False)
    assert Image.open(clipped).size == (200, 150)


def test_brace_without_label_draws_only_the_outline():
    canvas = Canvas(CanvasSpec(dpi=100)).extend(quadrant_axes(10, 10))
    canvas.add(BraceLayer("y", 2, 6, id="plain"))
    result = canvas.render()
    try:
        ax = result.axes
        assert _line(ax, "plain") is not None
        assert _texts(ax, "plain") == {}
    finally:
        result.close()


def test_blocked_inside_label_warns():
    from mosaickit import Fill, FillLayer, LayoutWarning

    canvas = Canvas(CanvasSpec(dpi=100)).extend(quadrant_axes(10, 10))
    canvas.add(FillLayer([(0, 0), (10, 0), (10, 10), (0, 10)], fill=Fill(opacity=0.2)))
    canvas.add(BraceLayer("y", 2, 6, "Span", id="b"))
    with pytest.warns(LayoutWarning, match="'b'"):
        canvas.render().close()


def test_unknown_axis_layer_subclass_is_rejected():
    from dataclasses import dataclass

    from mosaickit import RenderError
    from mosaickit.scene import AxisLayer

    @dataclass(frozen=True, slots=True)
    class Tick(AxisLayer):
        pass

    canvas = Canvas().add(Tick("y"))
    with pytest.raises(RenderError, match="Tick"):
        canvas.render()
