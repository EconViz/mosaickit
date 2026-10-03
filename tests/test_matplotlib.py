import pytest
from matplotlib.path import Path as MplPath

from mosaickit import (
    ArrowLayer,
    ArrowPlacement,
    ArrowStyle,
    Canvas,
    CanvasGrid,
    CanvasSpec,
    Fill,
    FillLayer,
    LegendLayer,
    LegendStyle,
    Marker,
    MarkerLayer,
    PathLayer,
    Span,
    Stroke,
    TextLayer,
    quadrant_axes,
)


def test_path_layers_render_ordered_coordinates_as_straight_segments():
    result = Canvas().add(PathLayer([(0, 0), (1, 4), (4, 0)])).render()
    try:
        path = result.axes.patches[0].get_path()
        assert path.codes.tolist() == [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO]
        assert path.vertices[1].tolist() == [1, 4]
    finally:
        result.close()


def test_fill_closes_an_open_coordinate_sequence_once():
    result = Canvas().add(FillLayer([(0, 0), (2, 0), (0, 2)])).render()
    try:
        path = result.axes.patches[0].get_path()
        assert path.codes.tolist() == [
            MplPath.MOVETO,
            MplPath.LINETO,
            MplPath.LINETO,
            MplPath.CLOSEPOLY,
        ]
        assert path.vertices.tolist() == [[0, 0], [2, 0], [0, 2], [0, 0]]
    finally:
        result.close()


def test_fill_marker_text_arrows_and_legend():
    canvas = (
        Canvas(CanvasSpec(dpi=72))
        .add(FillLayer([(0, 0), (2, 0), (0, 2)], fill=Fill(color="#12345680", opacity=0.5)))
        .add(MarkerLayer([(1, 1)], marker=Marker(size=50, opacity=0), id="point", legend="Point"))
        .add(TextLayer((1, 1), "x^2", math=True, offset=(3, 4)))
        .add(ArrowLayer((0, 0), (1, 1), arrow_placement=ArrowPlacement.BOTH))
        .add(LegendLayer(("point",)))
    )
    result = canvas.render()
    try:
        assert result.axes.patches[0].get_facecolor()[-1] == pytest.approx(128 / 255 * 0.5)
        assert result.axes.collections[0].get_facecolors()[0][-1] == 0
        assert result.axes.texts[0].get_text() == "$x^2$"
        assert result.axes.get_legend().get_texts()[0].get_text() == "Point"
        assert len(result.axes.patches) == 2
    finally:
        result.close()
        result.close()


@pytest.mark.parametrize(
    "placement,count",
    [(ArrowPlacement.START, 2), (ArrowPlacement.END, 2), (ArrowPlacement.BOTH, 3)],
)
def test_path_arrow_placements(placement, count):
    result = (
        Canvas()
        .add(
            PathLayer(
                [(0, 0), (1, 1)], stroke=Stroke(arrow=ArrowStyle.OPEN), arrow_placement=placement
            )
        )
        .render()
    )
    assert len(result.axes.patches) == count
    result.close()


def test_repeat_render_does_not_accumulate_or_mutate_global_state(tmp_path):
    import matplotlib
    from matplotlib import pyplot as plt

    params = dict(matplotlib.rcParams)
    figure_numbers = plt.get_fignums()
    canvas = Canvas(CanvasSpec(dpi=40)).add(PathLayer([(0, 0), (1, 1)], legend="line"))
    canvas.add(LegendLayer(style=LegendStyle(visible=False)))
    for _ in range(3):
        result = canvas.render()
        assert len(result.axes.patches) == 1
        assert result.axes.get_legend() is None
        result.close()
    for suffix in ("png", "pdf", "svg"):
        path = tmp_path / f"diagram.{suffix}"
        assert canvas.save(path) == [path]
        assert path.stat().st_size > 0
    assert dict(matplotlib.rcParams) == params
    assert plt.get_fignums() == figure_numbers


def test_grid_span_axes_size_and_repeated_saves(tmp_path):
    canvas = Canvas(CanvasSpec(dpi=40))
    grid = CanvasGrid([[canvas, canvas], [Span(canvas, cols=2)]])
    result = grid.render()
    assert len(result.axes) == 3
    assert result.axes[2].get_position().width > 2 * result.axes[0].get_position().width
    result.close()
    for _ in range(2):
        assert grid.save(tmp_path / "grid.png") == [tmp_path / "grid.png"]


@pytest.mark.parametrize(
    "anchor,ha,va",
    [
        ("left", "left", "center"),
        ("top", "center", "top"),
        ("top-left", "left", "top"),
        ("bottom-right", "right", "bottom"),
    ],
)
def test_text_anchor_sets_alignment(anchor, ha, va):
    result = Canvas().add(TextLayer((1, 1), "x", anchor=anchor)).render()
    try:
        text = result.axes.texts[0]
        assert text.get_horizontalalignment() == ha
        assert text.get_verticalalignment() == va
    finally:
        result.close()


def test_arrowheads_are_not_clipped_to_axes():
    from matplotlib.patches import FancyArrowPatch

    result = (
        Canvas()
        .add(PathLayer([(0, 0), (0, 10)], stroke=Stroke(arrow=ArrowStyle.OPEN)))
        .add(ArrowLayer((1, 1), (2, 2)))
        .render()
    )
    try:
        arrows = [p for p in result.axes.patches if isinstance(p, FancyArrowPatch)]
        assert len(arrows) == 2
        assert all(not arrow.get_clip_on() for arrow in arrows)
    finally:
        result.close()


def test_y_axis_arrowhead_draws_both_wings():
    import numpy as np

    from mosaickit import AxisSpec, build_axes

    canvas = Canvas(CanvasSpec(x_range=(0, 10), y_range=(0, 10), width=3, height=3, dpi=100))
    canvas.extend(
        build_axes(AxisSpec((0, 10), ArrowPlacement.END), AxisSpec((0, 10), ArrowPlacement.END))
    )
    result = canvas.render()
    try:
        result.figure.canvas.draw()
        pixels = np.asarray(result.figure.canvas.buffer_rgba())[:, :, :3]
        height = pixels.shape[0]
        x_px, y_px = result.axes.transData.transform((0, 10))
        row = int(round(height - y_px)) + 6  # a few pixels below the tip, inside the head
        col = int(round(x_px))
        left_wing = pixels[row, col - 5 : col - 1]
        right_wing = pixels[row, col + 2 : col + 6]
        assert left_wing.min() < 200, "left wing of the y-axis arrowhead is missing"
        assert right_wing.min() < 200, "right wing of the y-axis arrowhead is missing"
    finally:
        result.close()


def test_path_clip_flag_reaches_the_patch():
    result = (
        Canvas()
        .add(PathLayer([(0, 0), (1, 1)], id="clipped"))
        .add(PathLayer([(0, 0), (1, 1)], id="free", clip=False))
        .render()
    )
    try:
        by_id = {p.get_gid(): p for p in result.axes.patches}
        assert by_id["clipped"].get_clip_on() is True
        assert by_id["free"].get_clip_on() is False
    finally:
        result.close()


def test_axis_line_on_the_boundary_keeps_its_full_width():
    import numpy as np

    canvas = Canvas(CanvasSpec(x_range=(0, 10), y_range=(0, 10), width=3, height=3, dpi=300))
    result = canvas.extend(quadrant_axes(10, 10)).render()
    try:
        result.figure.canvas.draw()
        dark = np.asarray(result.figure.canvas.buffer_rgba())[:, :, :3].min(axis=2) < 200
        height = dark.shape[0]
        x_px, _ = result.axes.transData.transform((0, 0))
        col = int(round(x_px))

        def width_at(y):
            _, y_px = result.axes.transData.transform((0, y))
            return int(dark[int(round(height - y_px)), col - 8 : col + 8].sum())

        assert width_at(3) == width_at(9.5)
    finally:
        result.close()


def test_dashed_arrow_has_a_dashed_shaft_and_a_solid_head():
    from matplotlib.patches import FancyArrowPatch, PathPatch

    from mosaickit import DashStyle

    result = (
        Canvas()
        .add(ArrowLayer((1, 1), (1, 4), id="move", stroke=Stroke(dash=DashStyle.DASHED)))
        .render()
    )
    try:
        (shaft,) = [p for p in result.axes.patches if isinstance(p, PathPatch)]
        (head,) = [p for p in result.axes.patches if isinstance(p, FancyArrowPatch)]
        assert shaft.get_gid() == "move"
        assert shaft.get_linestyle() == "dashed"
        assert shaft.get_path().vertices.tolist() == [[1, 1], [1, 4]]
        assert head.get_linestyle() == "solid"
    finally:
        result.close()
