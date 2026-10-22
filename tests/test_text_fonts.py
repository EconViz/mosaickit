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
from mosaickit.rendering.matplotlib.text_layout import (
    default_files,
    text_typesetting,
    typesetter_for,
)

FONTS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
REGULAR = FONTS / "DejaVuSans.ttf"
BOLD = FONTS / "DejaVuSans-Bold.ttf"
SERIF = FONTS / "DejaVuSerif.ttf"
MONO = FONTS / "DejaVuSansMono.ttf"
STIX = FONTS / "STIXGeneral.ttf"  # a different face, to tell an override from the default


def _canvas(*layers, fonts=None, **options):
    spec = CanvasSpec(width=4, height=3, dpi=100)
    return Canvas(spec, config=Config(fonts=fonts), **options).extend(layers)


def _text(ax, gid):
    return next(t for t in ax.texts if t.get_gid() == gid)


def _width(text, *, fonts=None, **style):
    canvas = _canvas(
        TextLayer((5, 5), text, id="t", style=TextStyle(size=12, **style)), fonts=fonts
    )
    return _text(canvas.render().axes, "t").get_window_extent().width


def test_text_fonts_validate_their_files(tmp_path):
    assert TextFonts(REGULAR).sans == (REGULAR,)
    assert TextFonts([str(REGULAR), BOLD]).sans == (REGULAR, BOLD)
    assert TextFonts(serif=SERIF, mono=[MONO]).serif == (SERIF,)
    assert TextFonts().sans is None
    with pytest.raises(ConfigurationError, match="not a font file"):
        TextFonts(tmp_path / "missing.ttf")
    with pytest.raises(ConfigurationError, match="at least one"):
        TextFonts(serif=())
    with pytest.raises(ConfigurationError, match="font file or a list"):
        TextFonts(mono=[1])  # type: ignore[list-item]
    with pytest.raises(ConfigurationError, match="font file or a list"):
        TextFonts(sans={"a": REGULAR})  # type: ignore[arg-type]


def test_the_first_argument_is_still_the_sans_font_of_0_9_0():
    assert TextFonts((REGULAR, BOLD)).paths == (REGULAR, BOLD)
    assert TextFonts().paths == ()


def test_config_accepts_only_text_fonts():
    assert Config(fonts=TextFonts(REGULAR)).fonts == TextFonts(REGULAR)
    assert Config().fonts is None
    with pytest.raises(ConfigurationError, match="TextFonts"):
        Config(fonts=REGULAR)  # type: ignore[arg-type]


def test_toml_fonts_table_resolves_relative_files(tmp_path):
    (tmp_path / "a.ttf").write_bytes(REGULAR.read_bytes())
    config = Config.from_dict(
        {"fonts": {"sans": ["a.ttf", str(BOLD)], "mono": str(MONO)}}, base_dir=tmp_path
    )
    assert config.fonts == TextFonts((tmp_path / "a.ttf", BOLD), mono=MONO)
    assert Config.from_dict({"fonts": {"files": [str(SERIF)]}}).fonts == TextFonts(SERIF)
    assert Config.from_dict({}).fonts is None
    assert Config.from_dict({"fonts": {}}).fonts is None
    for bad, message in [
        ({"sans": []}, "non-empty"),
        ({"serif": 3}, "non-empty"),
        ({"font": "a.ttf"}, "unknown keys"),
        ({"sans": ["missing.ttf"]}, "not a font file"),
        ({"files": [str(SERIF)], "sans": [str(SERIF)]}, "give only one"),
    ]:
        with pytest.raises(ConfigurationError, match=message):
            Config.from_dict({"fonts": bad})
    with pytest.raises(ConfigurationError, match="table"):
        Config.from_dict({"fonts": "a.ttf"})


def test_text_has_a_default_font_without_any_configuration():
    ax = _canvas(TextLayer((5, 5), "label", id="t")).render().axes
    assert isinstance(_text(ax, "t"), MathText)


def test_the_three_generic_fonts_differ():
    widths = {name: _width("Generic text", font=name) for name in ("sans", "serif", "mono")}
    assert len(set(widths.values())) == 3
    assert _width("Generic text") == widths["sans"]  # sans is the default


def test_the_defaults_are_the_dejavu_files_matplotlib_installs():
    assert [f.name for f in default_files("sans")] == ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"]
    assert [f.name for f in default_files("serif")] == ["DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf"]
    assert [f.name for f in default_files("mono")] == [
        "DejaVuSansMono.ttf",
        "DejaVuSansMono-Bold.ttf",
    ]
    assert all(f.is_file() for slot in ("sans", "serif", "mono") for f in default_files(slot))


def test_a_given_slot_replaces_only_that_slot():
    plain = {name: _width("Override", font=name) for name in ("sans", "serif", "mono")}
    fonts = TextFonts(serif=STIX)
    assert _width("Override", fonts=fonts, font="serif") != plain["serif"]
    assert _width("Override", fonts=fonts, font="sans") == plain["sans"]
    assert _width("Override", fonts=fonts, font="mono") == plain["mono"]


def test_bold_picks_the_bold_face():
    typesetter = typesetter_for(TextFonts((REGULAR, BOLD)))
    regular = typesetter.layout("Weight", 12, 400)
    bold = typesetter.layout("Weight", 12, 700)
    assert bold.box[2] > regular.box[2]  # DejaVu Sans Bold is wider
    assert typesetter.layout("Weight", 12, 700) is bold  # cached


def test_weight_reaches_the_drawn_text():
    assert _width("Weight", weight="bold") > _width("Weight", weight="normal")
    assert _width("Weight", weight=700) == _width("Weight", weight="bold")
    assert _width("Weight", weight=None) == _width("Weight", weight="normal")


def test_a_missing_glyph_is_an_error_naming_the_text():
    with pytest.raises(RenderError, match="Cannot set text .* in the sans font"):
        _canvas(TextLayer((5, 5), "效用")).render()


def test_cjk_text_works_once_a_slot_has_a_cjk_font():
    # Matplotlib ships no CJK font; STIX has no CJK either, so this still fails clearly.
    with pytest.raises(RenderError, match="Cannot set text"):
        _canvas(TextLayer((5, 5), "效用"), fonts=TextFonts(sans=STIX)).render()


def test_text_mixed_with_math_stays_with_matplotlib():
    ax = _canvas(TextLayer((5, 5), "cost $c_1$", id="t")).render().axes
    assert not isinstance(_text(ax, "t"), MathText)


def test_measuring_matches_drawing():
    ax = _canvas(PointLabelLayer((5, 5), "Label", id="p")).render().axes
    style = TextStyle(size=10, rotation=0)
    with text_typesetting(None):
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
    with pytest.raises(ConfigurationError, match="Cannot load serif font"):
        _canvas(TextLayer((5, 5), "x"), fonts=TextFonts(serif=broken)).render()


def test_font_is_validated_and_survives_style_merging():
    for good in (None, "sans", "serif", "mono"):
        assert TextStyle(font=good).font == good
    for bad in ("monospace", "", 3, True):
        with pytest.raises(ConfigurationError, match="font"):
            TextStyle(font=bad)  # type: ignore[arg-type]
    merged = TextStyle(size=12).merged_over(TextStyle(font="serif", weight="bold"))
    assert (merged.font, merged.weight, merged.size) == ("serif", "bold", 12)
    assert StyleBundle(text=TextStyle(font="mono")).text.font == "mono"


def test_a_title_is_set_in_your_text_fonts():
    spec = CanvasSpec(width=4, height=3, dpi=100, title="Title")
    plain = Canvas(spec).render()
    yours = Canvas(spec, config=Config(fonts=TextFonts(STIX))).render()

    # Matplotlib keeps drawing the title when no fonts are given
    assert plain.axes.get_title() == "Title"
    assert yours.axes.get_title() == ""
    title = _text(yours.axes, "canvas.title")
    assert isinstance(title, MathText)
    box = title.get_window_extent(yours.figure.canvas.get_renderer())
    axes = yours.axes.get_window_extent()
    assert box.y0 >= axes.y1 and abs((box.x0 + box.x1) / 2 - (axes.x0 + axes.x1) / 2) < 1


def test_text_mixed_with_math_uses_your_file():
    from mosaickit.rendering.matplotlib.fonts import font_properties

    style = TextStyle(size=12, font="serif")
    assert font_properties(style).get_file() is None
    with text_typesetting(TextFonts(serif=SERIF)):
        assert Path(font_properties(style).get_file()) == SERIF
        assert font_properties(TextStyle(size=12)).get_file() is None  # sans not given
