import shutil
import subprocess

import pytest
from bezierkit import CubicBezierSegment, PiecewiseBezier, Point

from mosaickit import (
    ArrowLayer,
    Canvas,
    CanvasGrid,
    Fill,
    FillLayer,
    LegendLayer,
    MarkerLayer,
    PathLayer,
    Stroke,
    TextLayer,
)
from mosaickit.rendering.tikz import TikzOptions, TikzRenderer


def test_native_tikz_geometry_styles_and_fragments(tmp_path):
    segment = CubicBezierSegment(Point(0, 0), Point(1, 4), Point(2, 3), Point(4, 0))
    canvas = Canvas().add(PathLayer(segment, stroke=Stroke(color="#123456", width=2)))
    canvas.add(TextLayer((2, 2), "a_b & c"))
    target = tmp_path / "figure.tex"
    assert canvas.save(target, fragment=True, tikz_scale=2) == [target]
    text = target.read_text()
    assert "\\documentclass" not in text
    assert "controls (2.000000,8.000000) and (4.000000,6.000000) .. (8.000000,0.000000)" in text
    assert "line width=2pt" in text
    assert r"a\_b \& c" in text


def test_compound_subpaths_and_straight_segments_stay_native(tmp_path):
    lines = [
        CubicBezierSegment.from_line(Point(0, 0), Point(1, 0)),
        CubicBezierSegment.from_line(Point(1, 0), Point(1, 1)),
    ]
    path = PiecewiseBezier.compound(
        [
            PiecewiseBezier(lines),
            PiecewiseBezier([CubicBezierSegment.from_line(Point(3, 3), Point(4, 4))]),
        ]
    )
    output = tmp_path / "compound.tex"
    Canvas().add(PathLayer(path)).save(output)
    text = output.read_text()
    assert text.count("\\draw[") == 2
    assert text.count(".. controls") == 3
    assert "(1.000000,0.000000)" in text


def test_all_primitive_outputs_and_separate_mode_gate(tmp_path):
    canvas = (
        Canvas()
        .add(FillLayer([(0, 0), (2, 0), (0, 2)], fill=Fill(color="#377EB8", hatch="/")))
        .add(MarkerLayer([(1, 1)], id="point", legend="Point"))
        .add(TextLayer((2, 2), "x^2", math=True))
        .add(ArrowLayer((0, 0), (1, 1), label="Move"))
        .add(LegendLayer())
    )
    output = tmp_path / "all.tex"
    canvas.save(output)
    text = output.read_text()
    assert "-- cycle" in text
    assert "only marks" in text
    assert "$x^2$" in text
    assert "Point" in text
    assert "Move" in text
    assert "pattern=north east lines" in text
    with pytest.raises(NotImplementedError, match="to_tikz_separate"):
        canvas.save(output, mode="separate")
    with pytest.raises(NotImplementedError):
        canvas.save(output, renderer=TikzRenderer(TikzOptions("separate")))


def test_grid_tikz_scopes(tmp_path):
    canvas = Canvas().add(TextLayer((1, 1), "a"))
    output = tmp_path / "grid.tex"
    CanvasGrid([canvas, canvas]).save(output)
    assert output.read_text().count("\\begin{scope}") == 2


@pytest.mark.skipif(shutil.which("pdflatex") is None, reason="Optional LaTeX toolchain")
def test_standalone_tikz_compiles(tmp_path):
    canvas = (
        Canvas()
        .add(PathLayer([(0, 0), (1, 1)]))
        .add(MarkerLayer([(1, 1)], legend="Point"))
        .add(TextLayer((1, 1), "x", math=True))
        .add(FillLayer([(0, 0), (1, 0), (0, 1)], fill=Fill(hatch="/")))
        .add(ArrowLayer((0, 0), (1, 1)))
        .add(LegendLayer())
    )
    canvas.save(tmp_path / "figure.tex")
    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "figure.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout[-5000:]
