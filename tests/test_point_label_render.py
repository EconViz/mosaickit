import math
import warnings

import pytest

from mosaickit import (
    Canvas,
    CanvasGrid,
    FillLayer,
    LayoutWarning,
    MarkerLayer,
    PathLayer,
    PointLabelLayer,
    RegionLabelLayer,
    TextLayer,
)
from mosaickit.layout.geometry import Rect, rect_hits_segment, rect_overlaps_polygon

LINE_A = [(0, 0), (10, 10)]
LINE_B = [(0, 10), (10, 0)]
CROSSING = (5, 5)


def _display(ax, points):
    return tuple(tuple(float(v) for v in ax.transData.transform(p)) for p in points)


def _text(ax, gid):
    return next(t for t in ax.texts if t.get_gid() == gid)


def _rect(ax, artist):
    box = artist.get_window_extent(ax.figure.canvas.get_renderer())
    return Rect(box.x0, box.y0, box.x1, box.y1)


def _crossing_canvas():
    return (
        Canvas()
        .add(PathLayer(LINE_A, id="line_a"))
        .add(PathLayer(LINE_B, id="line_b"))
        .add(MarkerLayer([CROSSING], id="dot"))
    )


def test_label_at_a_crossing_touches_neither_line_nor_its_marker():
    result = _crossing_canvas().add(PointLabelLayer(CROSSING, "Crossing", id="dot.label")).render()
    try:
        ax = result.axes
        text = _text(ax, "dot.label")
        assert text.get_text() == "Crossing"
        rect = _rect(ax, text)
        for line in (LINE_A, LINE_B):
            assert not rect_hits_segment(rect, *_display(ax, line))
        (center,) = _display(ax, [CROSSING])
        assert not rect.inflate(3).contains(center)
        assert rect.within(Rect(*ax.bbox.extents))
        scale = ax.figure.dpi / 72
        assert math.dist(rect.nearest_point(center), center) < 25 * scale
    finally:
        result.close()


def test_label_avoids_existing_text_beside_the_point():
    result = (
        _crossing_canvas()
        .add(TextLayer(CROSSING, "Existing label", offset=(10, 2), anchor="left", id="existing"))
        .add(PointLabelLayer(CROSSING, "Crossing", id="dot.label"))
        .render()
    )
    try:
        ax = result.axes
        existing = next(t for t in ax.texts if t.get_text() == "Existing label")
        rect = _rect(ax, _text(ax, "dot.label"))
        assert not rect.intersects(_rect(ax, existing))
        for line in (LINE_A, LINE_B):
            assert not rect_hits_segment(rect, *_display(ax, line))
    finally:
        result.close()


def test_point_labels_avoid_each_other_and_other_markers():
    result = (
        Canvas()
        .add(MarkerLayer([(5, 5), (5.6, 5.2)], id="dots"))
        .add(PointLabelLayer((5, 5), "First point", id="first"))
        .add(PointLabelLayer((5.6, 5.2), "Second point", id="second"))
        .render()
    )
    try:
        ax = result.axes
        first, second = _rect(ax, _text(ax, "first")), _rect(ax, _text(ax, "second"))
        assert not first.intersects(second)
        (other,) = _display(ax, [(5.6, 5.2)])
        assert not first.inflate(3).contains(other)
    finally:
        result.close()


def test_label_avoids_filled_regions():
    region = [(5.2, 5.2), (10, 5.2), (10, 10), (5.2, 10)]
    result = (
        Canvas()
        .add(FillLayer(region, id="region"))
        .add(MarkerLayer([(5, 5)], id="dot"))
        .add(PointLabelLayer((5, 5), "Corner", id="dot.label"))
        .render()
    )
    try:
        ax = result.axes
        rect = _rect(ax, _text(ax, "dot.label"))
        assert not rect_overlaps_polygon(rect, _display(ax, region))
    finally:
        result.close()


def test_region_callouts_avoid_point_labels():
    # Point labels are placed first, so the region callout must work around them.
    small = [(5, 5), (5.3, 5), (5, 5.3)]
    result = (
        Canvas()
        .add(FillLayer(small, id="wedge"))
        .add(MarkerLayer([(6, 5.5)], id="dot"))
        .add(RegionLabelLayer("wedge", "Small region label", id="wedge.label"))
        .add(PointLabelLayer((6, 5.5), "Nearby point", id="dot.label"))
        .render()
    )
    try:
        ax = result.axes
        assert not _rect(ax, _text(ax, "wedge.label")).intersects(_rect(ax, _text(ax, "dot.label")))
    finally:
        result.close()


def test_crowded_point_warns_with_the_layer_id_and_still_renders():
    canvas = Canvas()
    for i in range(41):
        canvas.add(PathLayer([(0, i / 4), (10, i / 4)]))
    canvas.add(PointLabelLayer((5, 5.1), "Crowded point", id="crowded.label"))
    with pytest.warns(LayoutWarning, match="crowded.label"):
        result = canvas.render()
    try:
        assert _text(result.axes, "crowded.label").get_text() == "Crowded point"
    finally:
        result.close()


def test_point_labels_in_grid_panels_do_not_warn():
    def panel():
        return _crossing_canvas().add(PointLabelLayer(CROSSING, "Crossing", id="lbl"))

    with warnings.catch_warnings():
        warnings.simplefilter("error", LayoutWarning)
        result = CanvasGrid([[panel(), panel()]]).render()
    try:
        for ax in result.axes:
            assert [t.get_text() for t in ax.texts if t.get_gid() == "lbl"] == ["Crossing"]
    finally:
        result.close()
