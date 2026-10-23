import io
import re
import warnings

import matplotlib
import pytest

from mosaickit import (
    Canvas,
    CanvasSpec,
    Fill,
    FillLayer,
    LayoutWarning,
    MarkerLayer,
    Nudge,
    PathLayer,
    PointLabelLayer,
    RegionLabelLayer,
    SpanBraceLayer,
    TextLayer,
    nudge_from,
)
from mosaickit.layout.geometry import Rect
from mosaickit.rendering.tikz import canvas_to_tikz


def _render(layers, dpi=None):
    canvas = Canvas() if dpi is None else Canvas(CanvasSpec(dpi=dpi))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", LayoutWarning)
        return canvas.extend(layers).render()


def _box(result, gid):
    ax = result.axes
    (text,) = [t for t in ax.texts if t.get_gid() == gid]
    box = text.get_window_extent(ax.figure.canvas.get_renderer())
    return Rect(box.x0, box.y0, box.x1, box.y1)


def _shift(before, after):
    return (after.x0 - before.x0, after.y0 - before.y0)


def _boxes(layers_for, gid, dpi=None):
    """The label box without and with a nudge, and the pixels per point."""
    plain, moved = _render(layers_for(None), dpi), _render(layers_for(NUDGE), dpi)
    try:
        return _box(plain, gid), _box(moved, gid), moved.figure.dpi / 72
    finally:
        plain.close()
        moved.close()


NUDGE = nudge_from(top="10pt", left="4pt")  # up 10 pt, left 4 pt


def _point_scene(nudge):
    return [
        PathLayer([(0, 0), (10, 10)], id="line"),
        MarkerLayer([(4, 4)], id="dot"),
        PointLabelLayer((4, 4), "Point", id="dot.label", nudge=nudge),
    ]


@pytest.mark.parametrize("dpi", [None, 100])
def test_point_label_moves_by_the_nudge_after_placement(dpi):
    before, after, scale = _boxes(_point_scene, "dot.label", dpi)
    dx, dy = _shift(before, after)
    assert dx == pytest.approx(-4 * scale, abs=1e-6)
    assert dy == pytest.approx(10 * scale, abs=1e-6)
    assert (after.width, after.height) == pytest.approx((before.width, before.height))


def test_point_label_anchor_moves_in_data_coordinates_too():
    plain, moved = _render(_point_scene(None)), _render(_point_scene(Nudge(0, 10)))
    try:
        ax = moved.axes
        (a,) = [t for t in plain.axes.texts if t.get_gid() == "dot.label"]
        (b,) = [t for t in ax.texts if t.get_gid() == "dot.label"]
        start = ax.transData.transform(a.get_position())
        end = ax.transData.transform(b.get_position())
        scale = moved.figure.dpi / 72
        assert end[0] - start[0] == pytest.approx(0, abs=1e-6)
        assert end[1] - start[1] == pytest.approx(10 * scale, abs=1e-6)
    finally:
        plain.close()
        moved.close()


def test_labels_placed_later_avoid_the_nudged_box():
    def scene(nudge):
        return [
            MarkerLayer([(2, 2)], id="a"),
            MarkerLayer([(5, 5)], id="b"),
            PointLabelLayer((2, 2), "First", id="a.label", nudge=nudge),
            PointLabelLayer((5, 5), "Second", id="b.label"),
        ]

    solo = _render(scene(None))
    try:
        first, second = _box(solo, "a.label"), _box(solo, "b.label")
        scale = solo.figure.dpi / 72
    finally:
        solo.close()
    # Nudge the first label exactly onto the spot the second one took on its own.
    onto = Nudge(
        (second.center[0] - first.center[0]) / scale, (second.center[1] - first.center[1]) / scale
    )
    both = _render(scene(onto))
    try:
        moved_first, moved_second = _box(both, "a.label"), _box(both, "b.label")
    finally:
        both.close()
    assert moved_first.center == pytest.approx(second.center, abs=1e-6)
    assert not moved_second.intersects(moved_first)


def _region_scene(nudge):
    return [
        FillLayer([(0, 0), (10, 0), (0, 10)], fill=Fill(opacity=0.2), id="big"),
        RegionLabelLayer("big", "Inside", id="big.label", nudge=nudge),
    ]


def test_region_label_inside_moves_by_the_nudge():
    before, after, scale = _boxes(_region_scene, "big.label")
    assert _shift(before, after) == pytest.approx((-4 * scale, 10 * scale), abs=1e-6)


def _callout_scene(nudge):
    return [
        FillLayer([(4, 4), (4.3, 4), (4, 4.3)], fill=Fill(opacity=0.2), id="tiny"),
        RegionLabelLayer(
            "tiny", "A long callout label", id="tiny.label", placement="callout", nudge=nudge
        ),
    ]


def _leader(result, gid):
    ax = result.axes
    (line,) = [line for line in ax.lines if line.get_gid() == gid]
    return [tuple(ax.transData.transform(p)) for p in line.get_xydata()]


def test_callout_moves_and_its_leader_follows():
    plain, moved = _render(_callout_scene(None)), _render(_callout_scene(NUDGE))
    try:
        before, after = _box(plain, "tiny.label"), _box(moved, "tiny.label")
        scale = moved.figure.dpi / 72
        start_before, end_before = _leader(plain, "tiny.label.leader")
        start_after, end_after = _leader(moved, "tiny.label.leader")
    finally:
        plain.close()
        moved.close()
    assert _shift(before, after) == pytest.approx((-4 * scale, 10 * scale), abs=1e-6)
    assert start_after == pytest.approx(start_before)  # still leaves the region at the same spot
    # ...and ends at the moved label: 2 pt of padding plus a 2 pt gap short of its text.
    assert after.inflate(5 * scale).contains(end_after)
    assert end_after != pytest.approx(end_before)


def _brace_scene(nudge):
    return [SpanBraceLayer((2, 5), (6, 5), "Gap", id="gap", nudge=nudge)]


def test_brace_label_moves_by_the_nudge():
    before, after, scale = _boxes(_brace_scene, "gap.label")
    assert _shift(before, after) == pytest.approx((-4 * scale, 10 * scale), abs=1e-6)


@pytest.mark.parametrize("text", ["Text", "$x^2$"])
def test_text_layer_nudge_adds_to_its_offset(text):
    offset = _render([TextLayer((5, 5), text, offset=(-1, 13), id="t")])
    nudged = _render([TextLayer((5, 5), text, offset=(3, 3), nudge=Nudge(-4, 10), id="t")])
    try:
        assert _shift(_box(offset, "t"), _box(nudged, "t")) == pytest.approx((0, 0), abs=1e-6)
    finally:
        offset.close()
        nudged.close()


def test_tikz_shifts_text_by_offset_plus_nudge():
    canvas = Canvas().add(TextLayer((1, 1), "T", offset=(2, 3), nudge=Nudge(1, -1)))
    assert "xshift=3pt" in canvas_to_tikz(canvas)
    assert "yshift=2pt" in canvas_to_tikz(canvas)


def _svg(layers):
    with matplotlib.rc_context({"svg.hashsalt": "nudge-test"}):
        result = _render(layers)
        try:
            buffer = io.StringIO()
            result.figure.savefig(buffer, format="svg", metadata={"Date": None})
        finally:
            result.close()
    return re.sub(r'id="[^"]*"', "", buffer.getvalue())


def test_a_zero_or_missing_nudge_leaves_the_output_unchanged():
    def scene(nudge):
        return [
            FillLayer([(0, 0), (10, 0), (0, 10)], fill=Fill(opacity=0.2), id="big"),
            FillLayer([(8, 8), (8.3, 8), (8, 8.3)], fill=Fill(opacity=0.2), id="tiny"),
            MarkerLayer([(4, 4)], id="dot"),
            PointLabelLayer((4, 4), "Point", id="dot.label", nudge=nudge),
            RegionLabelLayer("big", "Inside", id="big.label", nudge=nudge),
            RegionLabelLayer("tiny", "Callout", id="tiny.label", nudge=nudge),
            SpanBraceLayer((2, 5), (6, 5), "Gap", id="gap", nudge=nudge),
            TextLayer((5, 9), "Text", offset=(2, 2), id="text", nudge=nudge),
        ]

    unset = _svg(scene(None))
    assert _svg(scene(Nudge())) == unset
    assert _svg(scene(NUDGE)) != unset
