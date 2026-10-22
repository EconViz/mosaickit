"""The scoped Matplotlib speedups change no drawing and leave Matplotlib as they found it."""

from __future__ import annotations

from contextlib import nullcontext

import matplotlib
import pytest
from matplotlib import mathtext
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties

from mosaickit import Canvas, PathLayer, PointLabelLayer, TextLayer
from mosaickit.rendering.matplotlib import renderer
from mosaickit.rendering.matplotlib.speedups import _MathtextCache, without_data_limits


def test_data_limits_are_skipped_only_inside_the_block() -> None:
    ax = Figure().add_subplot(111)
    with without_data_limits(ax):
        ax.plot([0, 10], [0, 10])
        assert tuple(ax.dataLim.intervalx) != (0.0, 10.0)
    assert "_update_line_limits" not in ax.__dict__
    ax.plot([0, 10], [0, 10])
    assert tuple(ax.dataLim.intervalx) == (0.0, 10.0)


def test_data_limits_are_restored_after_an_error() -> None:
    ax = Figure().add_subplot(111)
    with pytest.raises(RuntimeError), without_data_limits(ax):
        raise RuntimeError
    assert "_update_patch_limits" not in ax.__dict__


def test_the_mathtext_cache_returns_what_matplotlib_returns_and_restores_parse() -> None:
    original = mathtext.MathTextParser.parse
    cache = _MathtextCache()
    with cache.installed():
        assert mathtext.MathTextParser.parse is not original
        first = mathtext.MathTextParser("path").parse(r"$x^2$")
        again = mathtext.MathTextParser("path").parse(r"$x^2$")
    assert mathtext.MathTextParser.parse is original
    expected = mathtext.MathTextParser("path").parse(r"$x^2$")
    assert first is again
    assert first.width == expected.width and first.height == expected.height
    assert list(first.glyphs) == list(expected.glyphs)


def test_the_cache_key_includes_rcparams_and_font_properties() -> None:
    cache = _MathtextCache()
    with cache.installed():
        # a new parser per call, so Matplotlib's own per-instance cache cannot answer
        with matplotlib.rc_context({"mathtext.fontset": "stix"}):
            stix = mathtext.MathTextParser("path").parse(r"$x^2$")
        default = mathtext.MathTextParser("path").parse(r"$x^2$")
        large = mathtext.MathTextParser("path").parse(r"$x^2$", prop=FontProperties(size=20))
        assert stix is not default
        assert large is not default
        assert mathtext.MathTextParser("path").parse(r"$x^2$") is default


def test_installs_nest_and_restore_once() -> None:
    original = mathtext.MathTextParser.parse
    cache = _MathtextCache()
    with cache.installed():
        with cache.installed():
            pass
        assert mathtext.MathTextParser.parse is not original
    assert mathtext.MathTextParser.parse is original


def _canvas() -> Canvas:
    return (
        Canvas()
        .add(PathLayer([(0, 0), (10, 10)], id="a"))
        .add(TextLayer((2, 8), r"$U = x^{\alpha} y^{1-\alpha}$", id="t"))
        .add(PointLabelLayer((5, 5), r"$e^*$", id="p"))
    )


def test_a_drawing_is_identical_with_and_without_the_speedups(tmp_path, monkeypatch) -> None:
    def svg(name: str) -> str:
        path = tmp_path / name
        _canvas().save(str(path))
        text = path.read_text(encoding="utf-8")
        return "\n".join(line for line in text.splitlines() if "<dc:date>" not in line)

    matplotlib.rcParams["svg.hashsalt"] = "mosaickit"
    with_speedups = [svg("a.svg"), svg("b.svg")]  # the second draw hits the cache
    monkeypatch.setattr(renderer.mathtext_cache, "installed", lambda: nullcontext())
    monkeypatch.setattr(renderer, "without_data_limits", lambda ax: nullcontext())
    without = svg("c.svg")
    assert with_speedups[0] == with_speedups[1] == without
