import pytest

import mosaickit
from mosaickit import DEFAULT_PALETTE, Color, ConfigurationError, Palette
from mosaickit.themes import default

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


def test_default_theme_takes_every_color_from_the_palette():
    p = DEFAULT_PALETTE
    roles = default.roles
    assert roles["primary"].stroke.color == p["blue"]
    assert roles["secondary"].stroke.color == p["red"]
    assert roles["accent"].stroke.color == p["teal"]
    assert roles["guide"].stroke.color == p["grey-400"]
    assert roles["axes"].stroke.color == p["grey-800"]
    assert roles["canvas"].fill.color == p["white"]


def test_palette_is_exported():
    assert {"Palette", "DEFAULT_PALETTE"} <= set(mosaickit.__all__)
