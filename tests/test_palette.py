import pytest
from matplotlib.colors import to_hex

import mosaickit
from mosaickit import (
    DEFAULT_PALETTE,
    Canvas,
    Color,
    Config,
    ConfigurationError,
    Fill,
    Marker,
    Palette,
    PathLayer,
    Stroke,
    StyleBundle,
    TextStyle,
    Theme,
    use_config,
)
from mosaickit.rendering.plan import _build_render_plan
from mosaickit.themes import default
from mosaickit.themes.builtins import PRIMITIVE_DEFAULT

GREYS = {
    "grey-900": "#222222",
    "grey-800": "#333333",
    "grey-600": "#666666",
    "grey-400": "#999999",
    "grey-200": "#CCCCCC",
    "grey-100": "#E6E6E6",
}
HUES = {"blue": "#01A2D9", "red": "#E3120B", "teal": "#00887D"}


def test_default_palette_is_a_grey_ramp_plus_three_hues():
    assert DEFAULT_PALETTE.name == "default"
    assert {name: color.to_hex() for name, color in DEFAULT_PALETTE.colors.items()} == {
        **GREYS,
        "white": "#FFFFFF",
        **HUES,
    }


def test_palette_lookup_and_validation():
    palette = Palette("p", {"ink": "#000", "paper": Color(1, 1, 1)})
    assert palette["ink"] == Color(0, 0, 0)
    assert "paper" in palette and "missing" not in palette
    with pytest.raises(ConfigurationError, match="missing"):
        palette["missing"]
    with pytest.raises(ConfigurationError):
        Palette("p", {"bad": "red"})
    with pytest.raises(ConfigurationError):
        Palette("p", {"": "#000"})
    with pytest.raises(TypeError):
        palette.colors["ink"] = Color(1, 0, 0)  # type: ignore[index]


def test_default_theme_names_every_color_in_the_palette():
    roles = default.roles
    assert roles["primary"].stroke.color == "blue"
    assert roles["secondary"].stroke.color == "red"
    assert roles["accent"].stroke.color == "teal"
    assert roles["guide"].stroke.color == "grey-400"
    assert roles["axes"].stroke.color == "grey-800"
    assert roles["canvas"].fill.color == "white"
    assert PRIMITIVE_DEFAULT.stroke.color == "grey-800"
    assert PRIMITIVE_DEFAULT.text.color == "grey-900"


@pytest.mark.parametrize("style", [Stroke, Fill, TextStyle])
def test_style_colors_keep_names_and_parse_hex(style):
    assert style(color="accent").color == "accent"
    assert style(color="#123456").color == Color.from_hex("#123456")
    assert style(color=Color(0, 0, 0)).color == Color(0, 0, 0)
    with pytest.raises(ConfigurationError):
        style(color="")


def test_marker_edge_color_keeps_names():
    assert Marker(edge_color="accent").edge_color == "accent"


def _path_color(canvas: Canvas) -> str:
    result = canvas.render()
    try:
        return to_hex(result.axes.patches[0].get_edgecolor())
    finally:
        result.close()


def test_config_palette_recolors_default_theme_roles():
    palette = Palette("mine", {**DEFAULT_PALETTE.colors, "blue": "#123456"})
    with use_config(Config(palette=palette)):
        canvas = Canvas().add(PathLayer([(0, 0), (1, 1)], role="primary"))
    assert _path_color(canvas) == "#123456"
    assert _path_color(Canvas().add(PathLayer([(0, 0), (1, 1)], role="primary"))) == (
        DEFAULT_PALETTE["blue"].to_hex().lower()
    )


def test_custom_theme_names_resolve_against_config_palette():
    theme = Theme("mine", {"mypkg.line": StyleBundle(stroke=Stroke(color="accent"))})
    palette = Palette("mine", {**DEFAULT_PALETTE.colors, "accent": "#ABCDEF"})
    canvas = Canvas(config=Config(theme=theme, palette=palette))
    canvas.add(PathLayer([(0, 0), (1, 1)], role="mypkg.line"))
    assert _path_color(canvas) == "#abcdef"


def test_layer_styles_accept_names_and_hex():
    palette = Palette("mine", {**DEFAULT_PALETTE.colors, "accent": "#ABCDEF"})
    named = Canvas(config=Config(palette=palette)).add(
        PathLayer([(0, 0), (1, 1)], stroke=Stroke(color="accent"))
    )
    assert _path_color(named) == "#abcdef"
    hexed = Canvas().add(PathLayer([(0, 0), (1, 1)], stroke=Stroke(color="#123456")))
    assert _path_color(hexed) == "#123456"


def test_render_plan_holds_only_concrete_colors():
    canvas = Canvas().add(PathLayer([(0, 0), (1, 1)], role="primary"))
    (resolved,) = _build_render_plan(canvas.snapshot(), canvas._context()).layers
    style = resolved.style
    for value in (style.stroke.color, style.fill.color, style.marker.color, style.text.color):
        assert isinstance(value, Color)
    assert style.stroke.color == DEFAULT_PALETTE["blue"]


def test_unknown_color_name_raises_at_render():
    theme = Theme("mine", {"mypkg.boundary": StyleBundle(stroke=Stroke(color="missing"))})
    canvas = Canvas(config=Config(theme=theme))
    canvas.add(PathLayer([(0, 0), (1, 1)], role="mypkg.boundary"))
    with pytest.raises(ConfigurationError, match=r"mypkg.boundary.*stroke.color.*missing"):
        canvas.render()


def test_palette_without_a_name_used_by_the_theme_fails_clearly():
    canvas = Canvas(config=Config(palette=Palette("tiny", {"ink": "#000000"})))
    with pytest.raises(ConfigurationError, match=r"palette 'tiny' has no color"):
        canvas.render()


def test_palette_is_exported():
    assert {"Palette", "DEFAULT_PALETTE"} <= set(mosaickit.__all__)
