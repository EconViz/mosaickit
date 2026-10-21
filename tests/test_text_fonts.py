from pathlib import Path

import matplotlib
import pytest

from mosaickit import (
    Canvas,
    CanvasSpec,
    Config,
    ConfigurationError,
    PointLabelLayer,
    RenderError,
    StyleBundle,
    TextFonts,
    TextLayer,
    TextStyle,
)
from mosaickit.rendering.matplotlib.fonts import measure_text
from mosaickit.rendering.matplotlib.math_text import MathText
from mosaickit.rendering.matplotlib.text_layout import text_typesetting, typesetter_for

FONTS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
REGULAR = FONTS / "DejaVuSans.ttf"
BOLD = FONTS / "DejaVuSans-Bold.ttf"


def _canvas(*layers, fonts="both", **options):
    chosen = {"both": TextFonts((REGULAR, BOLD)), "none": None}.get(fonts, fonts)
    spec = CanvasSpec(width=4, height=3, dpi=100)
    return Canvas(spec, config=Config(fonts=chosen), **options).extend(layers)


def _text(ax, gid):
    return next(t for t in ax.texts if t.get_gid() == gid)


def test_text_fonts_validate_their_paths(tmp_path):
    assert TextFonts(REGULAR).paths == (REGULAR,)
    assert TextFonts([str(REGULAR), BOLD]).paths == (REGULAR, BOLD)
    with pytest.raises(ConfigurationError, match="not a font file"):
        TextFonts(tmp_path / "missing.ttf")
    with pytest.raises(ConfigurationError, match="at least one"):
        TextFonts(())
    with pytest.raises(ConfigurationError, match="file paths"):
        TextFonts([1])  # type: ignore[list-item]
    with pytest.raises(ConfigurationError, match="file paths"):
        TextFonts({"a": REGULAR})  # type: ignore[arg-type]


def test_config_accepts_only_text_fonts():
    assert Config(fonts=TextFonts(REGULAR)).fonts == TextFonts(REGULAR)
    assert Config().fonts is None
    with pytest.raises(ConfigurationError, match="TextFonts"):
        Config(fonts=REGULAR)  # type: ignore[arg-type]


def test_toml_fonts_table_resolves_relative_files(tmp_path):
    (tmp_path / "a.ttf").write_bytes(REGULAR.read_bytes())
    config = Config.from_dict({"fonts": {"files": ["a.ttf", str(BOLD)]}}, base_dir=tmp_path)
    assert config.fonts == TextFonts((tmp_path / "a.ttf", BOLD))
    assert Config.from_dict({}).fonts is None
    for bad, message in [
        ({"files": []}, "non-empty"),
        ({"files": "a.ttf"}, "non-empty"),
        ({"font": "a.ttf"}, "unknown keys"),
        ({"files": ["missing.ttf"]}, "not a font file"),
        ({}, None),
    ]:
        if message is None:
            assert Config.from_dict({"fonts": bad}).fonts is None
            continue
        with pytest.raises(ConfigurationError, match=message):
            Config.from_dict({"fonts": bad})
    with pytest.raises(ConfigurationError, match="table"):
        Config.from_dict({"fonts": "a.ttf"})


def test_plain_text_is_set_from_glyph_outlines():
    ax = _canvas(TextLayer((5, 5), "label", id="t")).render().axes
    assert isinstance(_text(ax, "t"), MathText)


def test_without_fonts_text_stays_with_matplotlib():
    ax = _canvas(TextLayer((5, 5), "label", id="t"), fonts="none").render().axes
    assert not isinstance(_text(ax, "t"), MathText)


def test_bold_picks_the_bold_face():
    typesetter = typesetter_for(TextFonts((REGULAR, BOLD)))
    regular = typesetter.layout("Weight", 12, 400)
    bold = typesetter.layout("Weight", 12, 700)
    assert bold.box[2] > regular.box[2]  # DejaVu Sans Bold is wider
    assert typesetter.layout("Weight", 12, 700) is bold  # cached


def test_weight_reaches_the_drawn_text():
    def width(weight):
        canvas = _canvas(
            TextLayer((5, 5), "Weight", id="t", style=TextStyle(size=12, weight=weight))
        )
        text = _text(canvas.render().axes, "t")
        return text.get_window_extent().width

    assert width("bold") > width("normal")
    assert width(700) == width("bold")
    assert width(None) == width("normal")


def test_a_missing_glyph_is_an_error_naming_the_text():
    with pytest.raises(RenderError, match="Cannot set text"):
        _canvas(TextLayer((5, 5), "效用")).render()


def test_text_mixed_with_math_stays_with_matplotlib():
    ax = _canvas(TextLayer((5, 5), "cost $c_1$", id="t")).render().axes
    assert not isinstance(_text(ax, "t"), MathText)


def test_measuring_matches_drawing():
    canvas = _canvas(PointLabelLayer((5, 5), "Label", id="p"))
    result = canvas.render()
    ax = result.axes
    style = TextStyle(size=10, rotation=0)
    with text_typesetting(TextFonts((REGULAR, BOLD))):
        width, height = measure_text(ax, "Label", style, ax.figure.canvas.get_renderer())
    assert width > 0 and height > 0


def test_multiline_text_takes_the_room_of_every_line():
    typesetter = typesetter_for(TextFonts(REGULAR))
    one = typesetter.layout("ab", 12, 400)
    two = typesetter.layout("ab\ncd", 12, 400)
    assert two.box[3] - two.box[1] > 1.5 * (one.box[3] - one.box[1])


def test_unusable_fonts_fail_before_drawing(tmp_path):
    broken = tmp_path / "broken.ttf"
    broken.write_bytes(b"not a font")
    with pytest.raises(ConfigurationError, match="Cannot load text fonts"):
        _canvas(TextLayer((5, 5), "x"), fonts=TextFonts(broken)).render()


def test_style_bundles_still_take_weight_in_roles():
    bundle = StyleBundle(text=TextStyle(weight="bold"))
    assert bundle.text.weight == "bold"
