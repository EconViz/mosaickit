from pathlib import Path

import pytest

from mosaickit import Canvas, CanvasGrid, ConfigurationError, Layout, Parameter, Span, TextLayer


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


@pytest.mark.parametrize("cell", [-1, 2, True, 1.0])
def test_grid_link_cells_must_exist(cell):
    from mosaickit import GridLink

    with pytest.raises(ConfigurationError, match="GridLink.end_cell"):
        CanvasGrid([Canvas(), Canvas()], rows=1, links=(GridLink(0, (0, 0), cell, (0, 0)),))
