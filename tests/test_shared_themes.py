import ast
import dataclasses
import re
from pathlib import Path

import pytest

from mosaickit import Color, ConfigurationError
from mosaickit.themes import (
    ROLES,
    SHARED_THEMES,
    ThemeTokens,
    get_tokens,
    list_shared_themes,
)

EXPECTED_NAMES = (
    "manual",
    "default",
    "colorblind",
    "monochrome",
    "nord",
    "paper",
    "presentation",
)

MANUAL = {
    "background": "#ffffff",
    "ink": "#1a1a1a",
    "primary": "#8c8c8c",
    "secondary": "#1a1a1a",
    "constraint": "#222222",
    "tertiary": "#6e6e6e",
    "accent": "#1a1a1a",
    "intervention": "#595959",
    "muted": "#8c8c8c",
    "subtle": "#b8b8b8",
    "series.1": "#8c8c8c",
    "series.2": "#8c8c8c",
    "series.3": "#8c8c8c",
    "fill.light": "#b8b8b8",
    "fill.mid": "#8c8c8c",
    "fill.dark": "#595959",
    "fill.faint": "#d9d9d9",
}


def test_roles():
    assert ROLES == tuple(MANUAL)
    assert len(set(ROLES)) == len(ROLES)


def test_theme_names():
    assert list_shared_themes() == EXPECTED_NAMES
    assert tuple(SHARED_THEMES) == EXPECTED_NAMES
    assert all(SHARED_THEMES[name].name == name for name in EXPECTED_NAMES)


def test_no_dark_theme():
    assert not any("dark" in name for name in list_shared_themes())
    with pytest.raises(ConfigurationError):
        get_tokens("dark")


@pytest.mark.parametrize("name", EXPECTED_NAMES)
def test_every_role_has_a_valid_colour(name):
    tokens = get_tokens(name)
    assert tuple(tokens.colors) == ROLES
    for role in ROLES:
        value = tokens.color(role)
        if role == "background" and name != "manual":
            assert value is None
            continue
        assert isinstance(value, str)
        assert re.fullmatch(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", value), (role, value)
        Color.from_hex(value)
    for scale in (tokens.line_scale, tokens.marker_scale, tokens.label_scale):
        assert isinstance(scale, float) and scale > 0


def test_manual_values_exactly():
    tokens = get_tokens("manual")
    assert dict(tokens.colors) == MANUAL
    assert (tokens.line_scale, tokens.marker_scale, tokens.label_scale) == (1.0, 1.0, 1.0)


def test_scales():
    presentation = get_tokens("presentation")
    assert (presentation.line_scale, presentation.marker_scale, presentation.label_scale) == (
        1.5,
        1.3,
        1.25,
    )
    for name in EXPECTED_NAMES:
        if name != "presentation":
            tokens = get_tokens(name)
            assert (tokens.line_scale, tokens.marker_scale, tokens.label_scale) == (1.0,) * 3


@pytest.mark.parametrize("name", ["default", "colorblind", "nord", "paper", "presentation"])
def test_fills_follow_the_curves(name):
    tokens = get_tokens(name)
    assert tokens.color("fill.light") == tokens.color("primary")
    assert tokens.color("fill.mid") == tokens.color("secondary")
    assert tokens.color("fill.dark") == tokens.color("accent")
    assert tokens.color("fill.faint") == tokens.color("intervention")


def test_monochrome_fill_ladder():
    tokens = get_tokens("monochrome")
    assert [tokens.color(f"fill.{k}") for k in ("light", "mid", "dark", "faint")] == [
        "#E0E0E0",
        "#BDBDBD",
        "#636363",
        "#969696",
    ]


def test_background_none_only_for_background():
    assert ThemeTokens("custom", {**MANUAL, "background": None}).color("background") is None
    with pytest.raises(ConfigurationError, match="'ink'"):
        ThemeTokens("custom", {**MANUAL, "ink": None})


def test_default_matches_colorblind():
    assert get_tokens("default").colors == get_tokens("colorblind").colors


def test_subtle_is_primary_at_45_percent():
    for name in EXPECTED_NAMES:
        if name == "manual":
            continue
        tokens = get_tokens(name)
        subtle = tokens.color("subtle")
        assert subtle == f"{tokens.color('primary')}73"
        assert Color.from_hex(subtle).alpha == pytest.approx(0.45, abs=0.005)


def test_get_tokens_normalises_name():
    assert get_tokens("  Nord ") is SHARED_THEMES["nord"]


@pytest.mark.parametrize("bad", ["solarized", "", None, 3])
def test_get_tokens_unknown_lists_names(bad):
    with pytest.raises(ConfigurationError) as info:
        get_tokens(bad)
    message = str(info.value)
    assert all(name in message for name in EXPECTED_NAMES)


def test_unknown_role():
    with pytest.raises(ConfigurationError, match="Unknown theme role"):
        get_tokens("default").color("nope")


def test_immutability():
    tokens = get_tokens("default")
    with pytest.raises(dataclasses.FrozenInstanceError):
        tokens.line_scale = 2.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        tokens.colors["primary"] = "#000000"  # type: ignore[index]
    with pytest.raises(TypeError):
        SHARED_THEMES["dark"] = tokens  # type: ignore[index]
    hash(tokens)


def test_tokens_copy_their_input():
    colors = dict(MANUAL)
    tokens = ThemeTokens("custom", colors)
    colors["primary"] = "#000000"
    assert tokens.color("primary") == "#8c8c8c"


@pytest.mark.parametrize(
    ("colors", "match"),
    [
        ({k: v for k, v in MANUAL.items() if k != "ink"}, "missing roles: ink"),
        ({**MANUAL, "extra": "#000000"}, "unknown roles: extra"),
        ({**MANUAL, "ink": "black"}, "'ink'"),
        ({**MANUAL, "ink": "#fff"}, "'ink'"),
        ({**MANUAL, "ink": "#12345"}, "'ink'"),
    ],
)
def test_validation(colors, match):
    with pytest.raises(ConfigurationError, match=match):
        ThemeTokens("custom", colors)


@pytest.mark.parametrize("scale", [0, -1.0, True, "1"])
def test_scale_validation(scale):
    with pytest.raises(ConfigurationError, match="line_scale"):
        ThemeTokens("custom", MANUAL, line_scale=scale)


def test_module_is_pure_data():
    import mosaickit.themes.shared as shared

    tree = ast.parse(Path(shared.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert imported <= {
        "__future__",
        "collections.abc",
        "dataclasses",
        "mosaickit.errors",
        "re",
        "types",
    }
