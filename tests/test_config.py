import asyncio

import pytest
from matplotlib.colors import to_hex

from mosaickit import (
    DEFAULT_PALETTE,
    Canvas,
    CanvasSpec,
    Color,
    Config,
    ConfigurationError,
    Palette,
    PathLayer,
    Theme,
    use_config,
)


def test_strict_toml_styles_and_source_errors(tmp_path):
    path = tmp_path / "diagram.toml"
    path.write_text('[canvas]\ndpi=72\n[styles."mypkg.boundary".stroke]\nwidth=2\nopacity=0\n')
    config = Config.load(path)
    assert config.canvas_spec.dpi == 72
    assert config.role_overrides["mypkg.boundary"].stroke.opacity == 0
    path.write_text('[styles."mypkg.boundary".stroke]\nwidht=2\n')
    with pytest.raises(ConfigurationError, match=r"diagram.toml.*mypkg.boundary.stroke"):
        Config.load(path)


@pytest.mark.parametrize(
    "data",
    [
        {"unknown": 1},
        {"styles": {"a.b": {"bad": {}}}},
        {"canvas": {"dpi": 0}},
        {"theme": "missing"},
    ],
)
def test_unknown_and_invalid_config(data):
    with pytest.raises(ConfigurationError):
        Config.from_dict(data)


def test_nested_defaults_restore_and_explicit_values_win():
    original = Canvas().spec
    with use_config(Config(canvas_spec=CanvasSpec(dpi=72))):
        assert Canvas().spec.dpi == 72
        with use_config(Config(canvas_spec=CanvasSpec(dpi=144))):
            assert Canvas().spec.dpi == 144
        assert Canvas().spec.dpi == 72
        assert Canvas(CanvasSpec(dpi=100)).spec.dpi == 100
        explicit = Theme("explicit", {})
        assert Canvas(theme=explicit).theme is explicit
    assert Canvas().spec == original


def test_contexts_are_isolated_between_concurrent_tasks():
    async def worker(dpi):
        with use_config(Config(canvas_spec=CanvasSpec(dpi=dpi))):
            await asyncio.sleep(0)
            return Canvas().spec.dpi

    async def run():
        return await asyncio.gather(worker(72), worker(144))

    assert asyncio.run(run()) == [72, 144]


def test_renderer_config_is_strict():
    with pytest.raises(ConfigurationError, match="renderer"):
        Config.from_dict({"renderer": {"name": "missing"}})


def test_toml_palette_layers_on_default_palette(tmp_path):
    path = tmp_path / "colors.toml"
    path.write_text('[palette]\nblue = "#123456"\naccent = "#ABCDEF"\n')
    palette = Config.load(path).palette
    assert palette["blue"] == Color.from_hex("#123456")
    assert palette["accent"] == Color.from_hex("#ABCDEF")
    assert palette["red"] == DEFAULT_PALETTE["red"]


def test_default_config_palette_is_the_default_palette():
    assert Config().palette == DEFAULT_PALETTE
    assert Config.from_dict({}).palette == DEFAULT_PALETTE


def test_python_palette_is_kept_as_given():
    palette = Palette("mine", {"ink": "#000000"})
    assert Config(palette=palette).palette is palette


def test_style_colors_accept_palette_names(tmp_path):
    path = tmp_path / "colors.toml"
    path.write_text(
        '[palette]\nblue = "#123456"\naccent = "#ABCDEF"\n'
        '[styles."mypkg.line".stroke]\ncolor = "blue"\n'
        '[styles."mypkg.line".fill]\ncolor = "accent"\n'
        '[styles."mypkg.line".marker]\ncolor = "teal"\nedge_color = "#000000"\n'
        '[styles."mypkg.line".text]\ncolor = "grey-900"\n'
    )
    bundle = Config.load(path).role_overrides["mypkg.line"]
    assert bundle.stroke.color == "blue"
    assert bundle.fill.color == "accent"
    assert bundle.marker.color == "teal"
    assert bundle.marker.edge_color == Color.from_hex("#000000")
    assert bundle.text.color == "grey-900"


def test_named_color_renders_with_config_palette(tmp_path):
    path = tmp_path / "colors.toml"
    path.write_text('[palette]\nblue = "#123456"\n[styles."mypkg.line".stroke]\ncolor = "blue"\n')
    with use_config(Config.load(path)):
        canvas = Canvas().add(PathLayer([(0, 0), (1, 1)], role="mypkg.line"))
    assert _path_color(canvas) == "#123456"


def test_toml_palette_recolors_default_theme_roles(tmp_path):
    path = tmp_path / "colors.toml"
    path.write_text('[palette]\nblue = "#123456"\nred = "#654321"\n')
    with use_config(Config.load(path)):
        primary = Canvas().add(PathLayer([(0, 0), (1, 1)], role="primary"))
        secondary = Canvas().add(PathLayer([(0, 0), (1, 1)], role="secondary"))
    assert _path_color(primary) == "#123456"
    assert _path_color(secondary) == "#654321"


def _path_color(canvas):
    result = canvas.render()
    try:
        return to_hex(result.axes.patches[0].get_edgecolor())
    finally:
        result.close()


def test_unknown_color_name_names_file_and_key(tmp_path):
    path = tmp_path / "colors.toml"
    path.write_text('[styles."mypkg.boundary".marker]\nedge_color = "missing"\n')
    with pytest.raises(
        ConfigurationError, match=r"colors.toml.*styles.mypkg.boundary.marker.edge_color.*missing"
    ):
        Config.load(path)


@pytest.mark.parametrize(
    ("palette", "match"),
    [
        ({"accent": "blue"}, r"palette.accent"),
        ({"accent": 3}, r"palette.accent"),
        ({"": "#000000"}, r"palette"),
        ("#000000", r"palette"),
    ],
)
def test_invalid_palette_section_names_file_and_key(tmp_path, palette, match):
    with pytest.raises(ConfigurationError, match=rf"colors.toml.*{match}"):
        Config.from_dict({"palette": palette}, source="colors.toml")


def test_python_palette_must_be_a_palette():
    with pytest.raises(ConfigurationError, match="palette"):
        Config(palette={"accent": "#123456"})  # type: ignore[arg-type]
