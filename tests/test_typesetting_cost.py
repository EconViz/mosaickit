"""Typesetting does its expensive work once: ink boxes per glyph, font files per used slot."""

from pathlib import Path

import matplotlib
import pytest

from mosaickit import MathFont, TextFonts
from mosaickit.rendering.matplotlib.math_text import MathTypesetter
from mosaickit.rendering.matplotlib.text_layout import TextTypesetter

FONTS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
FORMULAS = ("Y", r"\frac{M}{p_1}", r"LM\,\left(\frac{M}{p_1}\right)", r"\alpha^2 + y_0")
TOLERANCE = 1e-9


@pytest.mark.parametrize("formula", FORMULAS)
def test_math_box_matches_the_path_extents(formula):
    layout = MathTypesetter(MathFont(FONTS / "DejaVuSerif.ttf")).layout(formula, 12.0)
    ink = layout.path.get_extents()
    x0, y0, x1, y1 = layout.box
    assert x0 == pytest.approx(min(0.0, ink.x0), abs=TOLERANCE)
    assert y0 == pytest.approx(ink.y0, abs=TOLERANCE)
    assert x1 >= ink.x1 - TOLERANCE
    assert y1 == pytest.approx(ink.y1, abs=TOLERANCE)


def test_text_box_matches_the_path_extents():
    layout = TextTypesetter(TextFonts()).layout("Price level", 12.0, 400)
    ink = layout.path.get_extents()
    x0, y0, x1, y1 = layout.box
    assert x0 <= ink.x0 + TOLERANCE and y0 <= ink.y0 + TOLERANCE
    assert x1 >= ink.x1 - TOLERANCE and y1 >= ink.y1 - TOLERANCE


def test_each_glyph_ink_is_computed_once():
    typesetter = TextTypesetter(TextFonts())
    typesetter.layout("aaaa", 12.0, 400)
    assert len(typesetter._ink) == 1
    typesetter.layout("aaaab", 12.0, 400)
    assert len(typesetter._ink) == 2


def test_default_font_slots_load_when_first_used():
    typesetter = TextTypesetter(TextFonts())
    assert typesetter._libraries == {}
    typesetter.layout("x", 12.0, 400)
    assert list(typesetter._libraries) == ["sans"]
    typesetter.layout("x", 12.0, 400, "serif")
    assert list(typesetter._libraries) == ["sans", "serif"]


def test_given_font_files_still_load_up_front():
    typesetter = TextTypesetter(TextFonts(serif=(FONTS / "DejaVuSerif.ttf",)))
    assert list(typesetter._libraries) == ["serif"]
