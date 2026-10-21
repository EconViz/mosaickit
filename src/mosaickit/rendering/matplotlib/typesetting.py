"""One entry point for text that GlyphKit lays out instead of Matplotlib.

Math (``$...$``) goes through the math font and plain strings through the text fonts; either
may be absent, and a string neither handles is left to Matplotlib.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager

from mosaickit.math_font import MathFont
from mosaickit.rendering.matplotlib.math_text import MathLayout, math_typesetting
from mosaickit.rendering.matplotlib.math_text import typeset as typeset_math
from mosaickit.rendering.matplotlib.text_layout import text_typesetting, typeset_text
from mosaickit.text_fonts import TextFonts


@contextmanager
def typesetting(math_font: MathFont | None, text_fonts: TextFonts | None) -> Iterator[None]:
    """Typeset with the given fonts while drawing; None for either keeps Matplotlib's."""
    with ExitStack() as stack:
        stack.enter_context(math_typesetting(math_font))
        stack.enter_context(text_typesetting(text_fonts))
        yield


def typeset(text: str, style) -> MathLayout | None:
    """The GlyphKit layout of ``text`` in ``style``, or None when Matplotlib should draw it."""
    layout = typeset_math(text, style.size)
    if layout is not None:
        return layout
    return typeset_text(text, style)
