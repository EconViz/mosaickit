from __future__ import annotations

from dataclasses import dataclass

from mosaickit import (
    Canvas,
    CanvasGrid,
    Fill,
    FillLayer,
    GridSpacing,
    GroupLayer,
    Marker,
    MarkerLayer,
    PathLayer,
    Span,
    Stroke,
    StyleBundle,
    TextLayer,
    TextStyle,
)
from mosaickit.rendering.tikz import register_path_serializer


def test_canvas_saves_a_standalone_tikz_scene(tmp_path):
    canvas = Canvas()
    canvas.add(FillLayer([(0, 0), (2, 0), (1, 1)], fill=Fill(color="#984ea3", opacity=0.2)))
    canvas.add(PathLayer([(0, 0), (2, 1)], stroke=Stroke(color="#377eb8", width=2)))
    canvas.add(MarkerLayer([(1, 0.5)], marker=Marker(color="#e41a1c", size=9)))
    canvas.add(TextLayer((1, 0.5), "x^*", math=True))

    target = tmp_path / "scene.tex"
    assert canvas.save(target) == [target]

    source = target.read_text(encoding="utf-8")
    assert source.startswith(r"\documentclass[tikz,border=12pt]{standalone}")
    assert r"\begin{tikzpicture}" in source
    assert r"{$x^*$};" in source
    assert "377EB8" in source and "984EA3" in source and "E41A1C" in source


@dataclass(frozen=True)
class _Curve:
    token: str


def test_registered_geometry_serializer_controls_the_tikz_path(tmp_path):
    register_path_serializer(
        _Curve,
        lambda curve, options: rf"\draw[{options}] (0,0) .. controls {curve.token} .. (2,1);",
        replace=True,
    )
    canvas = Canvas().add(PathLayer([(0, 0), (2, 1)], model=_Curve("(0.5,1) and (1.5,1)")))

    target = tmp_path / "curve.tex"
    canvas.save(target)

    assert ".. controls (0.5,1) and (1.5,1) .." in target.read_text(encoding="utf-8")


def test_tikz_uses_resolved_group_layers_and_canvas_role_overrides(tmp_path):
    canvas = Canvas(role_overrides={"curve": StyleBundle(stroke=Stroke(color="#123456", width=3))})
    canvas.add(GroupLayer((PathLayer([(0, 0), (1, 1)], role="curve"),)))

    target = tmp_path / "group.tex"
    canvas.save(target)

    source = target.read_text(encoding="utf-8")
    assert "123456" in source
    assert "line width=3pt" in source


def test_canvas_grid_saves_a_standalone_tikz_layout(tmp_path):
    first = Canvas().add(TextLayer((0, 0), "first"))
    second = Canvas().add(TextLayer((0, 0), "second"))
    third = Canvas().add(TextLayer((0, 0), "third"))
    grid = CanvasGrid([[first, second], [Span(third, cols=2)]])

    target = tmp_path / "grid.tex"
    assert grid.save(target) == [target]

    source = target.read_text(encoding="utf-8")
    assert source.count(r"\begin{tikzpicture}") == 3
    assert "% row 1 of 2" in source
    assert "% row 2 of 2" in source
    assert r"\hspace{1em}" in source


def test_canvas_grid_tikz_export_uses_custom_proportional_spacing(tmp_path):
    canvas = Canvas()
    grid = CanvasGrid(
        [[canvas, canvas], [canvas, canvas]],
        spacing=GridSpacing(column_gap=0.25, row_gap=0.5, outer=0.1),
    )

    target = tmp_path / "spaced-grid.tex"
    grid.save(target)

    source = target.read_text(encoding="utf-8")
    assert r"\hspace{1.5in}" in source
    assert r"\par\vspace{3in}" in source
    assert source.count(r"\hspace*{1.2in}") == 4
    assert source.count(r"\vspace*{1.2in}") == 2
    assert r"\hspace{1em}" not in source


def _tikz_text(tmp_path, **style):
    canvas = Canvas().add(TextLayer((1, 1), "label", style=TextStyle(size=12, **style)))
    target = tmp_path / "text.tex"
    canvas.save(target)
    return target.read_text(encoding="utf-8")


def test_tikz_sets_the_generic_font_of_a_text_style(tmp_path):
    assert r"\sffamily" in _tikz_text(tmp_path)  # sans is the default
    assert r"\rmfamily" in _tikz_text(tmp_path, font="serif")
    assert r"\ttfamily" in _tikz_text(tmp_path, font="mono")


def test_canvas_grid_tikz_gap_only_spacing_keeps_the_centered_layout(tmp_path):
    canvas = Canvas()
    target = tmp_path / "gap.tex"
    CanvasGrid([[canvas, canvas]], spacing=GridSpacing(column_gap=0.5)).save(target)
    source = target.read_text(encoding="utf-8")
    assert r"\begin{center}" in source
    assert r"\hspace{3in}" in source
    assert r"\hspace*" not in source


def test_canvas_grid_tikz_default_spacing_is_unchanged(tmp_path):
    canvas = Canvas()
    plain, explicit = tmp_path / "a.tex", tmp_path / "b.tex"
    CanvasGrid([[canvas, canvas], [canvas, canvas]]).save(plain)
    CanvasGrid([[canvas, canvas], [canvas, canvas]], spacing=GridSpacing()).save(explicit)
    assert plain.read_text(encoding="utf-8") == explicit.read_text(encoding="utf-8")
