from pathlib import Path

import pytest

from mosaickit import (
    Canvas,
    CanvasGrid,
    CanvasSpec,
    ConfigurationError,
    GridSpacing,
    Layout,
    Parameter,
    Span,
    TextLayer,
)


class RecordingRenderer:
    name = "recording"

    def __init__(self):
        self.calls = []

    def render(self, scene, context):
        self.calls.append((scene, context))
        return scene

    def save(self, result, target, options):
        self.calls.append((target, options))
        return [target]


def test_canvas_snapshot_and_renderer_delegation(tmp_path):
    renderer = RecordingRenderer()
    canvas = Canvas(renderer=renderer)
    snapshot = canvas.snapshot()
    layer = TextLayer((1, 1), "label", id="label")
    assert canvas.add(layer) is canvas
    assert snapshot.layers == ()
    assert canvas.render().layers == (layer,)
    target = tmp_path / "diagram.svg"
    assert canvas.save(target) == [target]
    assert renderer.calls[-1][0] == Path(target)
    assert canvas.remove("label").snapshot().layers == ()
    assert canvas.add(layer).clear().snapshot().layers == ()


def test_span_placement_and_snapshot_isolation():
    first = Canvas().add(TextLayer((1, 1), "before"))
    grid = CanvasGrid([[Span(first, rows=2), Canvas()], [Canvas()]])
    assert (grid.rows, grid.cols) == (2, 2)
    assert [(p.row, p.col, p.rows, p.cols) for p in grid.placements] == [
        (0, 0, 2, 1),
        (0, 1, 1, 1),
        (1, 1, 1, 1),
    ]
    first.clear()
    assert len(grid.placements[0].canvas.snapshot().layers) == 1


@pytest.mark.parametrize(
    "layout,expected",
    [
        (Layout.TOP_TWO_BOTTOM_ONE, [(0, 0, 1), (0, 1, 1), (1, 0, 2)]),
        (Layout.TOP_ONE_BOTTOM_TWO, [(0, 0, 2), (1, 0, 1), (1, 1, 1)]),
    ],
)
def test_irregular_layouts_use_spans(layout, expected):
    grid = CanvasGrid.from_layout([Canvas(), Canvas(), Canvas()], layout)
    assert [(p.row, p.col, p.cols) for p in grid.placements] == expected


def test_flat_shape_inference_sweep_and_empty_cells():
    assert (CanvasGrid([Canvas()] * 5).rows, CanvasGrid([Canvas()] * 5).cols) == (2, 3)
    assert len(CanvasGrid([[Canvas(), None], [None, Canvas()]]).placements) == 2
    p = Parameter("x")
    grid = CanvasGrid.sweep(Canvas().add(TextLayer((p, 0), "x")), p.values([1, 2, 3]), cols=2)
    assert [item.canvas.snapshot().layers[0].position[0] for item in grid.placements] == [1, 2, 3]


def test_grid_spacing_is_public_and_propagates_through_factories():
    spacing = GridSpacing(column_gap=0.2, row_gap=0.1, outer=0.04)
    assert CanvasGrid([Canvas()], spacing=spacing).spacing is spacing
    parameter = Parameter("x")
    swept = CanvasGrid.sweep(Canvas(), parameter.values([1]), spacing=spacing)
    laid_out = CanvasGrid.from_layout([Canvas()], Layout.SINGLE, spacing=spacing)
    assert swept.spacing is spacing
    assert laid_out.spacing is spacing


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"column_gap": -0.1}, "column_gap.*negative"),
        ({"row_gap": float("inf")}, "row_gap.*finite"),
        ({"outer": 0.5}, "outer.*less than 0.5"),
        ({"outer": True}, "outer.*finite number"),
    ],
)
def test_grid_spacing_rejects_invalid_values(kwargs, match):
    with pytest.raises(ConfigurationError, match=match):
        GridSpacing(**kwargs)


def test_canvas_grid_rejects_an_untyped_spacing_value():
    with pytest.raises(ConfigurationError, match="CanvasGrid.spacing.*GridSpacing"):
        CanvasGrid([Canvas()], spacing={"column_gap": 0.2})


@pytest.mark.parametrize(
    "factory,match",
    [
        (lambda: Span(Canvas(), rows=0), "Span.rows"),
        (lambda: CanvasGrid([]), "at least"),
        (lambda: CanvasGrid([Canvas()] * 3, shape=(1, 2)), "too small"),
        (lambda: CanvasGrid([[Span(Canvas(), cols=3)]], cols=2), "row 0, cell 0"),
        (lambda: CanvasGrid([[Span(Canvas(), rows=2)]], rows=1), "row 0, cell 0"),
        (lambda: CanvasGrid([Canvas()], rows=0), "positive"),
    ],
)
def test_grid_errors_are_attributable(factory, match):
    with pytest.raises(ConfigurationError, match=match):
        factory()


def test_ragged_rows_require_explicit_empty_cells():
    with pytest.raises(ConfigurationError, match="row 1.*missing columns"):
        CanvasGrid([[Canvas(), Canvas()], [Canvas()]])
    assert len(CanvasGrid([[Canvas(), Canvas()], [Canvas(), None]]).placements) == 3


def test_grid_link_joins_points_in_two_cells_over_the_gap():
    from matplotlib.patches import ConnectionPatch

    from mosaickit import CanvasSpec, DashStyle, GridLink, Stroke

    spec = CanvasSpec(x_range=(0, 10), y_range=(0, 10))
    link = GridLink(0, (10, 4), 1, (0, 4), stroke=Stroke(dash=DashStyle.DASHED, color="red"))
    grid = CanvasGrid([Canvas(spec), Canvas(spec)], rows=1, links=(link,))
    result = grid.render()
    try:
        (patch,) = [a for a in result.figure.artists if isinstance(a, ConnectionPatch)]
        left, right = result.axes
        start = left.transData.transform((10, 4))
        end = right.transData.transform((0, 4))
        assert start[1] == pytest.approx(end[1])
        assert patch.get_linestyle() == "dashed"
        assert patch.xy1 == (10, 4) and patch.xy2 == (0, 4)
    finally:
        result.close()


def test_custom_spacing_moves_axes_and_grid_link_endpoints_together():
    from matplotlib.patches import ConnectionPatch

    from mosaickit import CanvasSpec, GridLink

    spec = CanvasSpec(x_range=(0, 10), y_range=(0, 10))
    grid = CanvasGrid(
        [Canvas(spec), Canvas(spec)],
        rows=1,
        links=(GridLink(0, (10, 5), 1, (0, 5)),),
        spacing=GridSpacing(column_gap=0.5, row_gap=0.25, outer=0.1),
    )
    result = grid.render()
    try:
        left, right = result.axes
        assert result.figure.subplotpars.wspace == pytest.approx(0.5)
        assert result.figure.subplotpars.hspace == pytest.approx(0.25)
        assert result.figure.subplotpars.left == pytest.approx(0.1)
        assert result.figure.subplotpars.right == pytest.approx(0.9)
        assert right.get_position().x0 - left.get_position().x1 > 0.1
        (patch,) = [a for a in result.figure.artists if isinstance(a, ConnectionPatch)]
        assert patch.xy1 == (10, 5) and patch.xy2 == (0, 5)
        assert patch.coords1 is left.transData
        assert patch.coords2 is right.transData
    finally:
        result.close()


@pytest.mark.parametrize("cell", [-1, 2, True, 1.0])
def test_grid_link_cells_must_exist(cell):
    from mosaickit import GridLink

    with pytest.raises(ConfigurationError, match="GridLink.end_cell"):
        CanvasGrid([Canvas(), Canvas()], rows=1, links=(GridLink(0, (0, 0), cell, (0, 0)),))


from mosaickit.rendering.matplotlib import grid_axes_size  # noqa: E402


def _mpl_default_positions(grid):
    from matplotlib.figure import Figure

    figure = Figure(figsize=grid.figure_size)
    slots = figure.add_gridspec(grid.rows, grid.cols)
    return [
        slots[p.row : p.row + p.rows, p.col : p.col + p.cols].get_position(figure).bounds
        for p in grid.placements
    ]


def test_unset_spacing_reproduces_the_previous_matplotlib_layout():
    spec = CanvasSpec(width=4, height=3)
    cells = [[Canvas(spec), Canvas(spec)], [Span(Canvas(spec), cols=2)]]
    for grid in (CanvasGrid(cells), CanvasGrid(cells, spacing=GridSpacing())):
        result = grid.render()
        try:
            actual = [ax.get_position().bounds for ax in result.axes]
            assert actual == pytest.approx(_mpl_default_positions(grid))
            assert result.figure.get_size_inches() == pytest.approx((8, 6))
        finally:
            result.close()


def test_explicit_spacing_sets_gaps_and_margins_in_figure_fractions():
    spec = CanvasSpec(width=4, height=3)
    grid = CanvasGrid(
        [[Canvas(spec), Canvas(spec)], [Canvas(spec), Canvas(spec)]],
        spacing=GridSpacing(column_gap=0.5, row_gap=0.25, outer=0.1),
    )
    result = grid.render()
    try:
        a, b, c, _ = (ax.get_position() for ax in result.axes)
        assert a.x0 == pytest.approx(0.1) and b.x1 == pytest.approx(0.9)
        assert c.y0 == pytest.approx(0.1) and a.y1 == pytest.approx(0.9)
        assert (b.x0 - a.x1) / a.width == pytest.approx(0.5)
        assert (a.y0 - c.y1) / a.height == pytest.approx(0.25)
        width, height = grid_axes_size(grid, 0)
        assert (width, height) == pytest.approx((a.width * 8, a.height * 6))
    finally:
        result.close()


def test_axes_size_matches_rendered_axes_for_spans_and_defaults():
    spec = CanvasSpec(width=4, height=3)
    for spacing in (None, GridSpacing(column_gap=0.3), GridSpacing(row_gap=0.4, outer=0.05)):
        grid = CanvasGrid(
            [[Canvas(spec), Canvas(spec)], [Span(Canvas(spec), cols=2)]], spacing=spacing
        )
        result = grid.render()
        try:
            for index, ax in enumerate(result.axes):
                box = ax.get_position()
                expected = (box.width * 8, box.height * 6)
                assert grid_axes_size(grid, index) == pytest.approx(expected)
        finally:
            result.close()
    with pytest.raises(ConfigurationError, match="does not exist"):
        grid_axes_size(grid, 5)


def test_grid_link_lands_on_the_data_points_with_custom_spacing():
    from matplotlib.patches import ConnectionPatch

    from mosaickit import GridLink

    spec = CanvasSpec(x_range=(0, 10), y_range=(0, 10))
    grid = CanvasGrid(
        [Canvas(spec), Canvas(spec)],
        rows=1,
        links=(GridLink(0, (10, 5), 1, (0, 5)),),
        spacing=GridSpacing(column_gap=0.8, outer=0.2),
    )
    result = grid.render()
    try:
        result.figure.canvas.draw()
        left, right = result.axes
        (patch,) = [a for a in result.figure.artists if isinstance(a, ConnectionPatch)]
        figure = result.figure
        start = patch.coords1.transform(patch.xy1)
        end = patch.coords2.transform(patch.xy2)
        left_box = left.get_window_extent()
        right_box = right.get_window_extent()
        assert start == pytest.approx((left_box.x1, (left_box.y0 + left_box.y1) / 2))
        assert end == pytest.approx((right_box.x0, (right_box.y0 + right_box.y1) / 2))
        assert end[0] - start[0] == pytest.approx(0.8 * left_box.width)
        assert figure is not None
    finally:
        result.close()


def _labelled_grid(spacing):
    from mosaickit import GridLink, MarkerLayer, PointLabelLayer

    spec = CanvasSpec(x_range=(0, 10), y_range=(0, 10), width=4, height=3)
    cells = [
        Canvas(spec)
        .add(MarkerLayer([(5, 5), (5.6, 5.2)], id="dots"))
        .add(PointLabelLayer((5, 5), "A", id="a"))
        .add(PointLabelLayer((5.6, 5.2), "B", id="b"))
        for _ in range(4)
    ]
    return CanvasGrid(cells, shape=(2, 2), links=(GridLink(0, (5, 5), 3, (5, 5)),), spacing=spacing)


def test_native_spacing_matches_adjusting_the_figure_after_rendering():
    from io import BytesIO

    gaps = dict(column_gap=0.22, row_gap=0.14, outer=0.02)
    native = _labelled_grid(GridSpacing(**gaps)).render()
    reference = _labelled_grid(None).render()
    try:
        reference.figure.subplots_adjust(
            left=gaps["outer"],
            right=1 - gaps["outer"],
            bottom=gaps["outer"],
            top=1 - gaps["outer"],
            wspace=gaps["column_gap"],
            hspace=gaps["row_gap"],
        )
        for one, other in zip(native.axes, reference.axes, strict=True):
            assert one.get_position().bounds == pytest.approx(other.get_position().bounds)
        for figure in (native.figure, reference.figure):
            figure.canvas.draw()
        for one, other in zip(native.axes, reference.axes, strict=True):
            for name in ("a", "b"):
                a = next(t for t in one.texts if t.get_gid() == name)
                b = next(t for t in other.texts if t.get_gid() == name)
                assert a.get_window_extent().extents == pytest.approx(b.get_window_extent().extents)
        images = []
        for result in (native, reference):
            buffer = BytesIO()
            result.figure.savefig(buffer, format="png")
            images.append(buffer.getvalue())
        assert images[0] == images[1]
    finally:
        native.close()
        reference.close()
