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
