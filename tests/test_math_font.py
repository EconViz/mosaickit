from pathlib import Path

import matplotlib
import pytest
from matplotlib.text import Text

from mosaickit import (
    AxisMarkLayer,
    BraceLayer,
    Canvas,
    CanvasSpec,
    Config,
    ConfigurationError,
    FillLayer,
    MarkerLayer,
    MathFont,
    PathLayer,
    PointLabelLayer,
    RegionLabelLayer,
    RenderError,
    SpanBraceLayer,
    Stroke,
    StyleBundle,
    TextLayer,
    TextStyle,
)
from mosaickit.rendering.matplotlib.fonts import measure_text
from mosaickit.rendering.matplotlib.math_text import MathText, math_typesetting, typesetter_for

FONTS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
# DejaVu Serif ships with Matplotlib and has an OpenType MATH table, so these tests
# need no font installed on the machine.
MATH_FONT = FONTS / "DejaVuSerif.ttf"
NO_MATH_TABLE = FONTS / "STIXGeneral.ttf"


def _canvas(*layers, font=MATH_FONT, **canvas_options):
    config = Config(math_font=MathFont(font) if font else None)
    spec = CanvasSpec(width=4, height=3, dpi=100)
    return Canvas(spec, config=config, **canvas_options).extend(layers)


def _render(*layers, font=MATH_FONT, **canvas_options):
    return _canvas(*layers, font=font, **canvas_options).render()


def _text(ax, gid):
    return next(t for t in ax.texts if t.get_gid() == gid)


def test_math_font_validates_its_path_and_flag(tmp_path):
    assert MathFont(str(MATH_FONT)).path == MATH_FONT
    assert MathFont(MATH_FONT).italic is True
    with pytest.raises(ConfigurationError, match="not a font file"):
        MathFont(tmp_path / "missing.otf")
    with pytest.raises(ConfigurationError, match="italic"):
        MathFont(MATH_FONT, italic="yes")  # type: ignore[arg-type]


def test_config_accepts_only_a_math_font():
    assert Config().math_font is None
    with pytest.raises(ConfigurationError, match="MathFont"):
        Config(math_font=str(MATH_FONT))  # type: ignore[arg-type]


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return path


def test_toml_math_table_resolves_relative_paths_beside_the_file(tmp_path):
    (tmp_path / "math.ttf").write_bytes(MATH_FONT.read_bytes())
    path = tmp_path / "diagram.toml"
    path.write_text('[math]\nfont = "math.ttf"\nitalic = false\n')
    config = Config.load(path)
    assert config.math_font == MathFont(tmp_path / "math.ttf", italic=False)
    assert Config.load(_write(tmp_path, "empty.toml", "[canvas]\ndpi = 72\n")).math_font is None


@pytest.mark.parametrize(
    "toml, message",
    [
        ('[math]\nfont = "missing.ttf"\n', "math:.*not a font file"),
        ("[math]\nitalic = true\n", "math.font is required"),
        ('[math]\nfont = "x.ttf"\nsize = 12\n', "unknown keys"),
        ("[math]\nfont = 3\n", "math.font must be a file path"),
    ],
)
def test_toml_math_table_errors_name_the_file_and_key(tmp_path, toml, message):
    path = _write(tmp_path, "bad.toml", toml)
    with pytest.raises(ConfigurationError, match=rf"bad.toml.*{message}"):
        Config.load(path)


def test_without_a_math_font_math_still_goes_through_mathtext():
    result = _render(
        TextLayer((5, 5), "f", math=True, id="f"),
        PointLabelLayer((2, 2), "$e$", id="e"),
        AxisMarkLayer("y", 3, "I_3", math=True, id="mark"),
        font=None,
    )
    try:
        assert not any(isinstance(t, MathText) for t in result.axes.texts)
        assert {t.get_text() for t in result.axes.texts} >= {"$f$", "$e$", "$I_3$"}
    finally:
        result.close()


def test_math_labels_use_glyphkit_outlines_when_a_math_font_is_set():
    result = _render(
        TextLayer((5, 5), "f", math=True, id="f"),
        TextLayer((5, 6), "$g$", offset=(4, 4), anchor="bottom-left", id="g"),
        PointLabelLayer((2, 2), "$e$", id="e"),
        AxisMarkLayer("y", 3, "I_3", math=True, id="mark"),
        AxisMarkLayer("x", 3, "x_1^*", math=True, id="xmark"),
        PathLayer([(1, 8), (4, 8)], id="line"),
        SpanBraceLayer((1, 8), (4, 8), "$a+b$", id="span", side="above"),
        BraceLayer("y", 5, 7, "$c$", math=False, side="inside", id="inner"),
        TextLayer((8, 8), "plain", id="plain"),
    )
    try:
        ax = result.axes
        for gid in ("f", "g", "e", "mark", "xmark", "span.label", "inner.label"):
            assert isinstance(_text(ax, gid), MathText), gid
        assert not isinstance(_text(ax, "plain"), MathText)
        assert _text(ax, "f").get_text() == "$f$"
    finally:
        result.close()


def test_text_mixed_with_math_and_unsupported_markup_is_left_to_mathtext():
    result = _render(
        TextLayer((5, 5), "price $p$ falls", id="mixed"),
        TextLayer((5, 6), "$a$ and $b$", id="two"),
    )
    try:
        assert all(type(_text(result.axes, gid)) is not MathText for gid in ("mixed", "two"))
    finally:
        result.close()


def test_placement_reserves_the_size_that_is_drawn():
    result = _render(
        MarkerLayer([(5, 5)], id="dot"),
        PointLabelLayer((5, 5), "$u(x_1, x_2)$", id="dot.label"),
    )
    try:
        ax = result.axes
        renderer = ax.figure.canvas.get_renderer()
        label = _text(ax, "dot.label")
        box = label.get_window_extent(renderer)
        style = TextStyle(size=12, rotation=0)
        with math_typesetting(MathFont(MATH_FONT)):
            width, height = measure_text(ax, "$u(x_1, x_2)$", style, renderer)
        assert (box.width, box.height) == pytest.approx((width, height))
        # The label is drawn where the placement pass put it: clear of the marker.
        x, y = ax.transData.transform((5, 5))
        assert not (box.x0 <= x <= box.x1 and box.y0 <= y <= box.y1)
    finally:
        result.close()


def test_rotation_swaps_the_measured_box():
    typesetter = typesetter_for(MathFont(MATH_FONT))
    layout = typesetter.layout("x_1", 12)
    width, height = layout.measure(2.0, 0)
    turned = layout.measure(2.0, 90)
    assert turned == pytest.approx((height, width))


def test_letters_are_italic_and_operators_are_spaced():
    upright = typesetter_for(MathFont(MATH_FONT, italic=False))
    italic = typesetter_for(MathFont(MATH_FONT))
    assert (
        italic.layout("a", 12).path.vertices.tolist()
        != upright.layout("a", 12).path.vertices.tolist()
    )

    def width(source):
        layout = italic.layout(source, 12)
        return layout.box[2] - layout.box[0]

    assert width("a=b") > width("a") + width("=") + width("b")
    assert width("a-b") > width("a") + width("-") + width("b")
    # A leading minus is a sign, not a binary operator: no space is inserted.
    assert width("-a") < width("a") + width("-") + 1
    # Scripts stay tight.
    assert width("x^{a=b}") < width("x") + width("a=b")


def test_math_font_changes_the_drawn_pixels(tmp_path):
    layer = TextLayer((5, 5), "f", math=True, style=TextStyle(size=40))
    before, after = tmp_path / "before.png", tmp_path / "after.png"
    _canvas(layer, font=None).save(before)
    paths = _canvas(layer).save(after)
    assert paths == [after]
    assert after.stat().st_size > 0
    assert before.read_bytes() != after.read_bytes()


@pytest.mark.parametrize("suffix", [".png", ".pdf", ".svg"])
def test_every_raster_and_vector_format_renders(tmp_path, suffix):
    canvas = _canvas(
        FillLayer([(1, 1), (1, 4), (4, 1)], id="tri"),
        RegionLabelLayer("tri", "$A_1$", id="tri.label"),
        PointLabelLayer((8, 8), "$c$", id="c"),
    )
    (path,) = canvas.save(tmp_path / f"out{suffix}")
    assert path.stat().st_size > 0


def test_grid_and_style_sizes_reach_the_math_layout():
    small = typesetter_for(MathFont(MATH_FONT)).layout("a", 10)
    large = typesetter_for(MathFont(MATH_FONT)).layout("a", 20)
    assert large.box[2] == pytest.approx(2 * small.box[2])
    result = _render(
        TextLayer((5, 5), "a", math=True, id="a", style=TextStyle(size=30)),
        TextLayer((5, 2), "a", math=True, id="b", style=TextStyle(size=15)),
    )
    try:
        renderer = result.axes.figure.canvas.get_renderer()
        big = _text(result.axes, "a").get_window_extent(renderer)
        little = _text(result.axes, "b").get_window_extent(renderer)
        assert big.width == pytest.approx(2 * little.width)
    finally:
        result.close()


def test_a_font_without_a_math_table_is_a_configuration_error():
    with pytest.raises(ConfigurationError, match="no OpenType MATH table"):
        _render(TextLayer((5, 5), "f", math=True), font=NO_MATH_TABLE)


def test_a_file_that_is_not_a_font_is_a_configuration_error(tmp_path):
    bogus = tmp_path / "notes.otf"
    bogus.write_text("not a font")
    with pytest.raises(ConfigurationError, match="Cannot load math font"):
        _render(font=bogus)


def test_math_the_font_layout_cannot_set_is_a_render_error():
    with pytest.raises(RenderError, match=r"Cannot set math '\\\\nonsense'"):
        _render(TextLayer((5, 5), r"\nonsense", math=True))


def test_stroke_and_theme_overrides_do_not_disturb_math_text():
    result = _render(
        TextLayer((5, 5), "f", math=True, id="f"),
        PathLayer([(1, 1), (2, 2)], stroke=Stroke(width=2)),
        role_overrides={"text": StyleBundle(text=TextStyle(color="#984EA3", size=18))},
    )
    try:
        assert _text(result.axes, "f").get_color() == pytest.approx(
            (152 / 255, 78 / 255, 163 / 255, 1.0)
        )
    finally:
        result.close()


def test_plain_text_class_is_unchanged_for_non_math_labels():
    result = _render(TextLayer((5, 5), "hello", id="hello"))
    try:
        assert isinstance(_text(result.axes, "hello"), Text)
        assert not isinstance(_text(result.axes, "hello"), MathText)
    finally:
        result.close()
