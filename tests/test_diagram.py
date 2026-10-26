"""The declarative diagram builder."""

import pytest

from mosaickit import CanvasGrid, GridSpacing, Nudge, TextLayer
from mosaickit.diagram import Diagram, indexed, link_points, primed, stack
from mosaickit.errors import ConfigurationError
from mosaickit.layout import centered_view
from mosaickit.scene import ArrowLayer, AxisMarkLayer, MarkerLayer, PointLabelLayer


def by_id(diagram, layer_id):
    return next(layer for layer in diagram.layers() if layer.id == layer_id)


def test_axes_titles_and_origin():
    d = Diagram(10, 8, x_label="$Y$", y_label="price", origin_label="0")
    ids = {layer.id for layer in d.layers()}
    assert {"axes.x", "axes.y", "axes.x.label", "axes.y.label", "axes.origin.label"} <= ids
    assert by_id(d, "axes.x.label").math is True
    assert by_id(d, "axes.y.label").math is False


def test_rejects_bad_extent_and_view_conflict():
    with pytest.raises(ConfigurationError):
        Diagram(0, 5)
    with pytest.raises(ConfigurationError):
        Diagram()
    with pytest.raises(ConfigurationError):
        Diagram(5, 5, view=centered_view([(1, 1), (2, 2)], gap_share=0.5))


def test_view_shifts_everything():
    view = centered_view([(4.0, 3.0), (6.0, 5.0)], gap_share=0.5)
    d = Diagram(view=view).point("A", (4.0, 3.0), "$A$")
    assert (d.x_max, d.y_max) == (view.x_span, view.y_span)
    assert d.at("A") == view.shift((4.0, 3.0))
    assert d.points["A"] == (4.0, 3.0)
    assert by_id(d, "A").points == (view.shift((4.0, 3.0)),)


def test_curve_trimmed_and_named_without_collision():
    d = Diagram(10, 10)
    d.curve("down", [(0, 10), (10, 0)], role="demand", label="$D$")
    path = by_id(d, "down").path
    assert max(x for x, _ in path) <= 9.2 + 1e-9
    label = by_id(d, "down.label")
    assert label.role == "demand" and label.offset != (0, 0)


def test_curve_must_enter_plot():
    with pytest.raises(ConfigurationError):
        Diagram(10, 10).curve("c", [(20, 20), (30, 30)])


def test_rising_names_upper_right_option():
    rising = [(0, 0), (8, 8)]
    plain = Diagram(10, 10).curve("s", rising, label="S")
    fancy = Diagram(10, 10, rising_names_upper_right=True).curve("s", rising, label="S")
    assert by_id(fancy, "s.label").anchor == "bottom-left"
    assert by_id(plain, "s.label").anchor != "bottom-left"


def test_names_avoid_each_other_and_fixed_side():
    d = Diagram(10, 10)
    d.curve("a", [(0, 0), (8, 8)], label="A")
    d.curve("b", [(0, 0.2), (8, 8.1)], label="B")
    assert by_id(d, "a.label").anchor != by_id(d, "b.label").anchor or (
        by_id(d, "a.label").offset != by_id(d, "b.label").offset
    )
    forced = Diagram(10, 10).curve("c", [(0, 0), (8, 8)], label="C", side="left")
    assert by_id(forced, "c.label").anchor == "right"
    with pytest.raises(ConfigurationError):
        Diagram(10, 10).curve("c", [(0, 0), (8, 8)], side="north")


def test_line_has_tails():
    d = Diagram(20, 20).line("is", [(5, 5), (10, 10)], tail=0.5)
    path = by_id(d, "is").path
    assert path[0][0] < 5 and path[-1][0] > 10


def test_points_guides_drop_and_arrows():
    d = Diagram(10, 10)
    d.point("E", (4, 6), "$E$", nudge=Nudge(2, 3))
    d.drop("E", x="$Y_0$", y="$p_0$")
    d.point("F", (6, 6))
    d.arrow("shift", "E", "F", label="$\\Delta$")
    guide = by_id(d, "E.x.guide")
    assert guide.path == ((4, 0), (4, 6)) and guide.role == "guide"
    assert by_id(d, "E.y.guide").path == ((0, 6), (4, 6))
    mark = by_id(d, "E.x.mark")
    assert isinstance(mark, AxisMarkLayer) and mark.math and mark.label == "Y_0"
    assert isinstance(by_id(d, "E.label"), PointLabelLayer)
    assert by_id(d, "E.label").nudge == Nudge(2, 3)
    arrow = by_id(d, "shift")
    assert isinstance(arrow, ArrowLayer) and (arrow.start, arrow.end) == ((4, 6), (6, 6))
    assert by_id(d, "shift.label").anchor == "bottom"
    assert not any(isinstance(layer, MarkerLayer) and layer.id == "F.label" for layer in d.layers())


def test_drop_with_view_uses_shifted_axes():
    view = centered_view([(4.0, 3.0), (6.0, 5.0)], gap_share=0.5)
    d = Diagram(view=view).point("A", (4.0, 3.0))
    d.drop("A", x="$x$", y="$y$")
    assert by_id(d, "A.x.guide").path[0] == (4.0 - view.x_origin, 0.0)
    assert by_id(d, "A.x.mark").value == pytest.approx(4.0 - view.x_origin)


def test_unknown_point_and_unnamed_drop():
    d = Diagram(10, 10)
    with pytest.raises(ConfigurationError):
        d.guide("nope", (1, 1), name="g")
    with pytest.raises(ConfigurationError):
        d.drop((1, 1), x="x")


def test_nudge_callback_adds_to_own_nudge():
    seen = []

    def nudge(layer):
        seen.append(layer.id)
        return Nudge(1, 1) if layer.id == "E.label" else None

    d = Diagram(10, 10, nudge=nudge).point("E", (1, 1), "E", nudge=Nudge(2, 0))
    assert by_id(d, "E.label").nudge == Nudge(3, 1)
    assert "E.label" in seen
    assert any(isinstance(layer, TextLayer) for layer in Diagram(10, 10, x_label="x").layers())


def test_id_prefix_and_roles():
    d = Diagram(10, 10, id_prefix="p.", axes_role="frame").curve("c", [(0, 1), (5, 5)])
    assert by_id(d, "p.c").role == "curve"
    assert by_id(d, "p.axes.x").role == "frame"


def test_canvas_renders():
    d = Diagram(10, 10, x_label="$Y$", y_label="$p$", origin_label="0")
    d.curve("d", [(0, 9), (9, 0)], label="$D$").point("E", (4, 5), "$E$").drop("E", x="$Y_0$")
    result = d.canvas().render()
    assert result is not None


def test_labels_helpers():
    assert indexed("$Y$", 1) == "$Y_1$" and indexed("Y", 2) == "Y_2"
    assert primed("$A$", 2) == "$A''$" and primed("A", 1) == "A'" and primed("$A$", 0) == "$A$"


def test_stack_links_resolve_to_panel_points():
    top = Diagram(10, 10).point("A", (3, 4)).point("B", (6, 5))
    view = centered_view([(3.0, 1.0), (6.0, 2.0)], gap_share=0.5)
    bottom = Diagram(view=view).point("A", (3, 1)).point("B", (6, 2))
    grid = stack(
        [top, bottom],
        link_points(0, 1, ["A", "B"], role="macro.link"),
        spacing=GridSpacing(row_gap=0.2),
    )
    assert isinstance(grid, CanvasGrid) and (grid.rows, grid.cols) == (2, 1)
    first = grid.links[0]
    assert (first.start_cell, first.start, first.end_cell) == (0, (3, 4), 1)
    assert first.end == view.shift((3, 1)) and first.role == "macro.link"
    assert grid.spacing.row_gap == 0.2


def test_stack_validates():
    with pytest.raises(ConfigurationError):
        stack([])
    with pytest.raises(ConfigurationError):
        stack([Diagram(1, 1).point("A", (0, 0))], link_points(0, 3, ["A"]))
    with pytest.raises(ConfigurationError):
        stack([Diagram(1, 1)], link_points(0, 0, ["missing"]))


def test_two_panel_derivation_saves(tmp_path):
    """A derivation in ~20 lines: an IS-LM style panel above a derived curve."""
    prices = [1.0, 1.5, 2.0]
    outputs = [8.0, 6.5, 5.0]
    rates = [3.0, 4.0, 5.0]
    upper = centered_view([(outputs[0], rates[0]), (outputs[-1], rates[-1])], gap_share=0.5)
    lower = centered_view([(outputs[0], prices[0]), (outputs[-1], prices[-1])], gap_share=0.5)
    top = Diagram(view=upper, x_label="$Y$", y_label="$i$", origin_label="0")
    bottom = Diagram(view=lower, x_label="$Y$", y_label="$p$", origin_label="0")
    top.line("is", [(9.0, 3.0), (5.0, 5.0)], tail=0.2, label="IS")
    bottom.line("ad", list(zip(outputs, prices, strict=True)), tail=0.2, label="AD")
    for i, (y, i_rate, p) in enumerate(zip(outputs, rates, prices, strict=True)):
        top.curve(f"lm{i}", [(y - 2, i_rate - 1), (y + 2, i_rate + 1)], label=f"LM{i}")
        top.point(f"E{i}", (y, i_rate), f"E{i}")
        bottom.point(f"E{i}", (y, p), f"E{i}").drop(f"E{i}", x=f"Y{i}", y=f"p{i}")
    grid = stack(
        [top, bottom], link_points(0, 1, ["E0", "E1", "E2"]), spacing=GridSpacing(row_gap=0.2)
    )
    assert grid.save(tmp_path / "ad.png") == [tmp_path / "ad.png"]
    assert (tmp_path / "ad.png").stat().st_size > 0
