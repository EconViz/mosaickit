import pytest

import mosaickit
from mosaickit import (
    Canvas,
    ConfigurationError,
    LayoutWarning,
    MarkerLayer,
    PathLayer,
    SpanBraceLayer,
)
from mosaickit.layout.geometry import Rect, rect_hits_segment


def test_span_brace_model_defaults_and_export():
    layer = SpanBraceLayer((2, 5), (6, 5), "Gap")
    assert (layer.start, layer.end, layer.label, layer.side) == (
        (2.0, 5.0),
        (6.0, 5.0),
        "Gap",
        "below",
    )
    assert layer.style_slots == {"stroke": "stroke", "text": "style"}
    assert "SpanBraceLayer" in mosaickit.__all__


@pytest.mark.parametrize(
    "factory",
    [
        lambda: SpanBraceLayer((1, 1), (1, 1)),  # empty span
        lambda: SpanBraceLayer((1, 1), (3, 2)),  # neither horizontal nor vertical
        lambda: SpanBraceLayer((1, 1), (3, 1), side="left"),  # side across a horizontal span
        lambda: SpanBraceLayer((1, 1), (1, 3), side="below"),  # side across a vertical span
        lambda: SpanBraceLayer((1, 1), (3, 1), side="middle"),
    ],
)
def test_span_brace_rejects_invalid_input(factory):
    with pytest.raises(ConfigurationError):
        factory()


def _render(*layers):
    return Canvas().extend(layers).render()


def _brace_and_label(result, gid):
    (brace,) = [line for line in result.axes.lines if line.get_gid() == gid]
    labels = [t for t in result.axes.texts if t.get_gid() == f"{gid}.label"]
    return brace, labels


def test_horizontal_span_brace_hangs_below_the_line_with_its_label_under_it():
    line = [(0, 5), (10, 5)]
    result = _render(
        PathLayer(line, id="line"),
        MarkerLayer([(3, 5), (7, 5)], id="dots"),
        SpanBraceLayer((3, 5), (7, 5), "Gap", id="gap"),
    )
    try:
        ax = result.axes
        brace, (label,) = _brace_and_label(result, "gap")
        to_px = ax.transData.transform
        line_y = to_px((0, 5))[1]
        xs, ys = zip(*to_px(brace.get_xydata()), strict=True)
        assert max(ys) < line_y  # entirely below the line
        assert min(xs) == pytest.approx(to_px((3, 5))[0], abs=1)
        assert max(xs) == pytest.approx(to_px((7, 5))[0], abs=1)
        box = label.get_window_extent(ax.figure.canvas.get_renderer())
        assert box.y1 < min(ys) + 1  # label below the brace tip
        a, b = (tuple(p) for p in to_px(line))
        assert not rect_hits_segment(Rect(box.x0, box.y0, box.x1, box.y1), a, b)
    finally:
        result.close()


@pytest.mark.parametrize("side", ["above", "below"])
def test_brace_bulges_to_the_requested_side(side):
    result = _render(SpanBraceLayer((3, 5), (7, 5), side=side, id="b"))
    try:
        ax = result.axes
        brace, labels = _brace_and_label(result, "b")
        assert labels == []
        line_y = ax.transData.transform((0, 5))[1]
        ys = [y for _, y in ax.transData.transform(brace.get_xydata())]
        assert (min(ys) > line_y) if side == "above" else (max(ys) < line_y)
    finally:
        result.close()


def test_vertical_span_brace_on_the_right_and_its_label_avoids_lines():
    blocker = [(6.3, 0), (6.3, 10)]  # a line right where the label would first go
    result = _render(
        PathLayer(blocker, id="blocker"),
        SpanBraceLayer((5, 3), (5, 7), "Span", side="right", id="v"),
    )
    try:
        ax = result.axes
        brace, (label,) = _brace_and_label(result, "v")
        to_px = ax.transData.transform
        xs = [x for x, _ in to_px(brace.get_xydata())]
        assert min(xs) > to_px((5, 0))[0]
        box = label.get_window_extent(ax.figure.canvas.get_renderer())
        a, b = (tuple(p) for p in to_px(blocker))
        assert not rect_hits_segment(Rect(box.x0, box.y0, box.x1, box.y1), a, b)
    finally:
        result.close()


def test_crowded_span_brace_label_warns():
    lines = [PathLayer([(0, y / 4), (10, y / 4)]) for y in range(0, 41)]
    with pytest.warns(LayoutWarning, match="crowded"):
        result = _render(*lines, SpanBraceLayer((3, 5), (7, 5), "Gap", id="crowded"))
    result.close()


def test_label_with_no_room_under_the_tip_moves_out_on_a_leader():
    # A narrow span between a vertical line and a steep line: nothing fits right
    # under the brace, so the label is pulled out with a leader instead of covering.
    vertical = [(4.5, 0), (4.5, 9)]
    steep = [(1.5, 8), (7.5, 1)]
    result = _render(
        PathLayer(vertical, id="vertical"),
        PathLayer(steep, id="steep"),
        SpanBraceLayer((4.5, 3.5), (5.214, 3.5), "Long label text", id="narrow"),
    )
    try:
        ax = result.axes
        _, (label,) = _brace_and_label(result, "narrow")
        leaders = [line for line in ax.lines if line.get_gid() == "narrow.leader"]
        assert len(leaders) == 1
        box = label.get_window_extent(ax.figure.canvas.get_renderer())
        rect = Rect(box.x0, box.y0, box.x1, box.y1)
        for line in (vertical, steep):
            a, b = (tuple(p) for p in ax.transData.transform(line))
            assert not rect_hits_segment(rect, a, b)
    finally:
        result.close()
