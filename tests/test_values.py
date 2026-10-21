import warnings
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from mosaickit import (
    TRANSPARENT,
    CanvasSpec,
    Color,
    ConfigurationError,
    Fill,
    Interval,
    LegendStyle,
    Marker,
    Stroke,
    TextStyle,
)


@pytest.mark.parametrize("lo,hi", [(0, 0), (2, 1), (float("nan"), 1), (0, float("inf"))])
def test_invalid_intervals(lo, hi):
    with pytest.raises(ConfigurationError):
        Interval(lo, hi)
    with pytest.raises(ConfigurationError, match="x_range"):
        CanvasSpec(x_range=(lo, hi))


def test_canvas_spec_is_immutable_and_replace_validates():
    spec = CanvasSpec()
    assert (spec.x_min, spec.x_max, spec.y_min, spec.y_max) == (0, 10, 0, 10)
    assert spec.replace(x_range=[-1, 2]).x_range == (-1, 2)
    assert hash(spec) == hash(CanvasSpec())
    with pytest.raises(FrozenInstanceError):
        spec.dpi = 72
    with pytest.raises(ConfigurationError):
        spec.replace(width=-1)


@pytest.mark.parametrize(
    "values",
    [
        {"width": 0},
        {"height": float("inf")},
        {"width": float("nan")},
        {"dpi": 0},
        {"dpi": 1201},
        {"dpi": 72.5},
        {"dpi": True},
        {"x_range": (1,)},
    ],
)
def test_canvas_rejects_invalid_values(values):
    with pytest.raises(ConfigurationError):
        CanvasSpec(**values)


@pytest.mark.parametrize(
    "hex_value,expected",
    [
        ("#abc", "#AABBCC"),
        ("#123456", "#123456"),
        ("#12345680", "#12345680"),
    ],
)
def test_color_round_trip(hex_value, expected):
    color = Color.from_hex(hex_value)
    assert color.to_hex() == expected
    assert Color.from_channels(*color.channels) == color
    assert hash(color) == hash(Color.from_hex(expected))


@pytest.mark.parametrize("value", ["red", "#12", "#12345", "#GG0000", "123456"])
def test_invalid_hex(value):
    with pytest.raises(ConfigurationError):
        Color.from_hex(value)


@pytest.mark.parametrize("channel", [-0.1, 1.1, float("nan"), float("inf")])
def test_color_channel_bounds(channel):
    with pytest.raises(ConfigurationError):
        Color(channel, 0, 0)


def test_transparent_color():
    assert TRANSPARENT.to_hex() == "#00000000"
    assert Color(0, 0, 0).to_hex(include_alpha=True) == "#000000FF"


@pytest.mark.parametrize("style", [Stroke, Fill, Marker, TextStyle, LegendStyle])
def test_sparse_merge_preserves_every_field(style):
    values = {
        "color": "#123456",
        "edge_color": "#112233",
        "opacity": 0,
        "width": 0,
        "size": 0,
        "edge_width": 0,
        "visible": False,
        "frame": False,
        "location": "upper left",
        "dash": "dotted",
        "arrow": "open",
        "hatch": "x",
        "shape": "s",
        "family": "serif",
        "weight": "bold",
        "font": "serif",
        "rotation": 0,
    }
    full = style(**{field.name: values[field.name] for field in fields(style)})
    assert style().merged_over(full) == full
    assert full.merged_over(style()) == full


@pytest.mark.parametrize("style", [Stroke, Fill, Marker, TextStyle])
@pytest.mark.parametrize("opacity", [-1, 2, float("nan")])
def test_style_opacity_validation(style, opacity):
    with pytest.raises(ConfigurationError):
        style(opacity=opacity)


def test_styles_do_not_cross_merge():
    with pytest.raises(TypeError):
        Marker(size=3).merged_over(TextStyle(size=12))


@pytest.mark.parametrize(
    "font_fields", [{"family": "serif"}, {"family": "serif", "weight": "bold"}]
)
def test_legacy_family_warns_once_at_caller_and_preserves_fields(font_fields):
    with pytest.warns(DeprecationWarning, match="GlyphKit") as caught:
        style = TextStyle(**font_fields)
    assert len(caught) == 1
    assert caught[0].category is DeprecationWarning
    assert Path(caught[0].filename) == Path(__file__)
    for name, value in font_fields.items():
        assert getattr(style, name) == value


@pytest.mark.parametrize("weight", ["normal", "bold", 1, 400, 700, 1000])
def test_weight_is_not_deprecated_and_accepts_glyphkit_values(weight):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert TextStyle(weight=weight).weight == weight
    assert not caught


@pytest.mark.parametrize("weight", ["heavy", "", 0, 1001, 4.5, True, -1])
def test_weight_rejects_values_glyphkit_cannot_resolve(weight):
    with pytest.raises(ConfigurationError, match="weight"):
        TextStyle(weight=weight)


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"family": None, "weight": None},
        {"weight": "bold"},
        {"color": "#123456", "size": 12, "opacity": 0.5, "rotation": 45},
    ],
)
def test_default_and_non_font_text_styles_remain_warning_free(values):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        TextStyle(**values)
    assert not caught


def test_internal_text_style_copies_preserve_fonts_without_repeating_warning():
    from mosaickit import Canvas, Parameter, TextLayer
    from mosaickit.rendering.plan import _build_render_plan

    with pytest.warns(DeprecationWarning, match="GlyphKit"):
        style = TextStyle(color="blue", family="DejaVu Serif", weight="bold")
    p = Parameter("x")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        merged = TextStyle(size=14).merged_over(style)
        canvas = Canvas().add(TextLayer((p, 5), "text", style=merged)).bind(p, 2)
        plan = _build_render_plan(canvas.snapshot(), canvas._context())
    assert not caught
    assert plan.layers[0].style.text.family == "DejaVu Serif"
    assert plan.layers[0].style.text.weight == "bold"
    assert plan.layers[0].style.text.size == 14
