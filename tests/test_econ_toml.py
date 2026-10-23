"""The shared econ-viz.toml sections every EconViz package reads."""

from pathlib import Path

import pytest
from matplotlib import get_data_path

from mosaickit import ConfigurationError, econ_toml

FONTS = Path(get_data_path()) / "fonts" / "ttf"


def test_reads_the_shared_sections_and_resolves_paths(tmp_path):
    (tmp_path / "fonts").mkdir()
    for name in ("DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf"):
        (tmp_path / "fonts" / name).write_bytes((FONTS / name).read_bytes())
    path = tmp_path / econ_toml.FILE_NAME
    path.write_text(
        'base = "default"\n'
        '[font]\ntext = "serif"\nmath = "fonts/math.otf"\n'
        '[fonts]\nserif = ["fonts/DejaVuSerif.ttf", "fonts/DejaVuSerif-Bold.ttf"]\n'
        '[color]\nbackground = "#ffffff"\naxis = "#1a1a1a"\nlabel = "#222222"\nic = "#8c8c8c"\n'
        '[principle.color]\ndemand = "#8c8c8c"\n',
        encoding="utf-8",
    )

    data = econ_toml.read(path)
    shared = econ_toml.shared_settings(data, base_dir=tmp_path)

    assert econ_toml.find(tmp_path) == path
    assert shared.base == "default"
    assert shared.font == "serif"
    assert shared.math_font == str(tmp_path / "fonts" / "math.otf")
    assert shared.fonts is not None
    assert shared.fonts.serif == (
        tmp_path / "fonts" / "DejaVuSerif.ttf",
        tmp_path / "fonts" / "DejaVuSerif-Bold.ttf",
    )
    assert (shared.background, shared.axis, shared.label) == ("#ffffff", "#1a1a1a", "#222222")
    assert econ_toml.package_table(data, "principle") == {"color": {"demand": "#8c8c8c"}}
    assert econ_toml.package_table(data, "macro") == {}


def test_missing_sections_keep_defaults():
    assert econ_toml.shared_settings({}) == econ_toml.SharedSettings()
    assert econ_toml.find(Path("/nonexistent-dir")) is None


@pytest.mark.parametrize(
    "data",
    [
        {"font": {"text": "fantasy"}},
        {"fonts": {"script": "a.ttf"}},
        {"fonts": {"serif": 3}},
        {"color": {"axis": 1}},
        {"base": 2},
        {"font": "serif"},
    ],
)
def test_rejects_bad_shared_values(data):
    with pytest.raises(ConfigurationError):
        econ_toml.shared_settings(data)


def test_package_table_names_are_checked():
    assert econ_toml.package_table({"utility": {"a": 1}}, "utility") == {"a": 1}
    with pytest.raises(ConfigurationError):
        econ_toml.package_table({}, "colour")
    with pytest.raises(ConfigurationError):
        econ_toml.package_table({"principle": 1}, "principle")


def test_bad_toml_names_the_file(tmp_path):
    path = tmp_path / "econ-viz.toml"
    path.write_text("[font\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="econ-viz.toml"):
        econ_toml.read(path)
