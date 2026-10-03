import warnings

import pytest

from mosaickit import (
    Canvas,
    CanvasGrid,
    CanvasSpec,
    FillLayer,
    LayoutWarning,
    MarkerLayer,
    PathLayer,
    RegionLabelLayer,
    RenderError,
    TextLayer,
)
from mosaickit.layout.geometry import (
    Rect,
    rect_hits_segment,
    rect_inside_polygon,
    rect_overlaps_polygon,
)


def _display(ax, points):
    return tuple(tuple(float(v) for v in ax.transData.transform(p)) for p in points)


def _text(ax, gid):
    return next(t for t in ax.texts if t.get_gid() == gid)


def _rect(ax, artist):
    box = artist.get_window_extent(ax.figure.canvas.get_renderer())
    return Rect(box.x0, box.y0, box.x1, box.y1)


def _leaders(ax, gid):
    return [line for line in ax.lines if line.get_gid() == f"{gid}.leader"]


def test_large_region_is_labelled_inside_without_a_leader():
    big = [(0, 0), (10, 0), (0, 10)]
    result = (
        Canvas()
        .add(FillLayer(big, id="big"))
        .add(RegionLabelLayer("big", "Large region", id="big.label"))
        .render()
    )
    try:
        ax = result.axes
        text = _text(ax, "big.label")
        assert text.get_text() == "Large region"
        assert rect_inside_polygon(_rect(ax, text), _display(ax, big))
        assert _leaders(ax, "big.label") == []
    finally:
        result.close()


def test_small_region_gets_a_callout_that_avoids_lines_points_and_regions():
    small = [(5, 5), (5.3, 5), (5, 5.3)]
    neighbour = [(6, 0), (10, 0), (10, 4)]
    line_a = [(0, 10), (10, 0)]
    line_b = [(0, 0), (10, 10)]
    result = (
        Canvas()
        .add(PathLayer(line_a, id="line_a"))
        .add(PathLayer(line_b, id="line_b"))
        .add(MarkerLayer([(5, 5)], id="dot"))
        .add(FillLayer(small, id="wedge"))
        .add(FillLayer(neighbour, id="other"))
        .add(RegionLabelLayer("wedge", "Small region label", id="wedge.label"))
        .render()
    )
    try:
        ax = result.axes
        rect = _rect(ax, _text(ax, "wedge.label"))
        for line in (line_a, line_b):
            assert not rect_hits_segment(rect, *_display(ax, line))
        assert not rect_overlaps_polygon(rect, _display(ax, small))
        assert not rect_overlaps_polygon(rect, _display(ax, neighbour))
        assert not rect.contains(_display(ax, [(5, 5)])[0])
        assert rect.within(Rect(*ax.bbox.extents))
        assert len(_leaders(ax, "wedge.label")) == 1
    finally:
        result.close()


def test_short_text_is_used_inside_when_the_full_text_does_not_fit():
    square = [(2, 2), (3.6, 2), (3.6, 3.6), (2, 3.6)]
    result = (
        Canvas()
        .add(FillLayer(square, id="r"))
        .add(RegionLabelLayer("r", "Small region label", short_text="SRL", id="r.label"))
        .render()
    )
    try:
        ax = result.axes
        text = _text(ax, "r.label")
        assert text.get_text() == "SRL"
        assert rect_inside_polygon(_rect(ax, text), _display(ax, square))
        assert _leaders(ax, "r.label") == []
    finally:
        result.close()


def test_forced_callout_and_forced_inside():
    big = [(0, 0), (10, 0), (0, 10)]
    out = (
        Canvas()
        .add(FillLayer(big, id="big"))
        .add(RegionLabelLayer("big", "A", placement="callout", id="l"))
        .render()
    )
    small = [(5, 5), (5.1, 5), (5, 5.1)]
    inside = (
        Canvas()
        .add(FillLayer(small, id="s"))
        .add(RegionLabelLayer("s", "Very long label", placement="inside", id="l"))
        .render()
    )
    try:
        assert len(_leaders(out.axes, "l")) == 1
        assert _leaders(inside.axes, "l") == []
    finally:
        out.close()
        inside.close()


def test_callout_avoids_existing_text():
    small = [(5, 5), (5.3, 5), (5, 5.3)]
    result = (
        Canvas()
        .add(FillLayer(small, id="s"))
        .add(TextLayer((6.2, 5.15), "Existing label", anchor="left", id="existing"))
        .add(RegionLabelLayer("s", "Small region label", id="s.label"))
        .render()
    )
    try:
        ax = result.axes
        existing = next(t for t in ax.texts if t.get_text() == "Existing label")
        assert not _rect(ax, _text(ax, "s.label")).intersects(_rect(ax, existing))
    finally:
        result.close()


def test_crowded_canvas_warns_and_still_renders():
    canvas = Canvas()
    for i in range(41):
        canvas.add(PathLayer([(0, i / 4), (10, i / 4)]))
    canvas.add(FillLayer([(5, 5), (5.1, 5), (5, 5.1)], id="s"))
    canvas.add(RegionLabelLayer("s", "Small region label", id="s.label"))
    with pytest.warns(LayoutWarning, match="s.label"):
        result = canvas.render()
    try:
        assert _text(result.axes, "s.label").get_text() == "Small region label"
    finally:
        result.close()


def test_unknown_region_id_is_a_render_error():
    with pytest.raises(RenderError, match="missing"):
        Canvas().add(RegionLabelLayer("missing", "A")).render()


def test_inline_polygon_region_in_grid_panels():
    def panel():
        return Canvas().add(RegionLabelLayer([(0, 0), (10, 0), (0, 10)], "Region", id="lbl"))

    with warnings.catch_warnings():
        warnings.simplefilter("error", LayoutWarning)
        result = CanvasGrid([[panel(), panel()]]).render()
    try:
        for ax in result.axes:
            assert [t.get_text() for t in ax.texts if t.get_gid() == "lbl"] == ["Region"]
    finally:
        result.close()


def test_callout_does_not_land_in_an_unfilled_pocket_between_regions():
    # Two shaded triangles with an unfilled strip between them: the strip is an
    # enclosed pocket, so the wedge's callout must not go there.
    result = (
        Canvas(CanvasSpec(x_range=(0, 12), y_range=(0, 14), width=7.2, height=5.2, dpi=150))
        .add(PathLayer([(0, 12), (10, 0)], id="line_a"))
        .add(PathLayer([(0, 2), (10, 10)], id="line_b"))
        .add(FillLayer([(0, 12), (0, 7.2), (4, 7.2)], id="upper"))
        .add(FillLayer([(0, 5.2), (0, 2), (4, 5.2)], id="lower"))
        .add(FillLayer([(4, 7.2), (4, 5.2), (5, 6)], id="wedge"))
        .add(PathLayer([(0, 0), (0, 14)], id="y-axis"))
        .add(RegionLabelLayer("wedge", "Small region label", id="wedge.label"))
        .render()
    )
    try:
        ax = result.axes
        (x0, y0), (x1, y1) = _display(ax, [(0, 5.2), (4, 7.2)])
        assert not _rect(ax, _text(ax, "wedge.label")).intersects(Rect(x0, y0, x1, y1))
    finally:
        result.close()


def test_callout_stays_on_its_side_of_a_crossing():
    # The wedge has the crossing (5, 6) of line_a and line_b as a vertex. Its label
    # must not sit past that crossing, where the two lines diverge.
    result = (
        Canvas(CanvasSpec(x_range=(0, 12), y_range=(0, 14), width=7.2, height=5.2, dpi=150))
        .add(PathLayer([(0, 12), (10, 0)], id="line_a"))
        .add(PathLayer([(0, 2), (10, 10)], id="line_b"))
        .add(FillLayer([(0, 12), (0, 7.2), (4, 7.2)], id="upper"))
        .add(FillLayer([(0, 7.2), (4, 7.2), (4, 5.2), (0, 5.2)], id="strip"))
        .add(FillLayer([(0, 5.2), (0, 2), (4, 5.2)], id="lower"))
        .add(FillLayer([(4, 7.2), (4, 5.2), (5, 6)], id="wedge"))
        .add(MarkerLayer([(5, 6), (4, 7.2), (4, 5.2)]))
        .add(RegionLabelLayer("wedge", "Small region label", id="wedge.label"))
        .render()
    )
    try:
        ax = result.axes
        ((cross_x, _),) = _display(ax, [(5, 6)])
        center_x, _ = _rect(ax, _text(ax, "wedge.label")).center
        assert center_x < cross_x
    finally:
        result.close()
