import asyncio

import pytest

from mosaickit import Canvas, CanvasSpec, Config, ConfigurationError, Theme, use_config


def test_strict_toml_styles_and_source_errors(tmp_path):
    path = tmp_path / "diagram.toml"
    path.write_text('[canvas]\ndpi=72\n[styles."utility.budget".stroke]\nwidth=2\nopacity=0\n')
    config = Config.load(path)
    assert config.canvas_spec.dpi == 72
    assert config.role_overrides["utility.budget"].stroke.opacity == 0
    path.write_text('[styles."utility.budget".stroke]\nwidht=2\n')
    with pytest.raises(ConfigurationError, match=r"diagram.toml.*utility.budget.stroke"):
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
