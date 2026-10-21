"""Plain text set from GlyphKit outlines when the caller chose text fonts.

The counterpart of ``math_text`` for ordinary strings. Without ``TextFonts`` nothing here
is active and text goes to Matplotlib exactly as before. With them, every string without
``$...$`` math is laid out by GlyphKit, turned into a path, and drawn as the same
``MathText`` artist the math path uses, so label placement, window extents and tight bounding
boxes see it like any other text, and measuring and drawing share one layout.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from typing import cast

from glyphkit import FontLibrary, FontSource, GlyphKitError, Paragraph, TextSpan
from glyphkit import TextStyle as GlyphStyle
from matplotlib.path import Path

from mosaickit.errors import ConfigurationError, RenderError
from mosaickit.rendering.matplotlib.math_text import _MOVETO, MathLayout, _append_outline
from mosaickit.text_fonts import TextFonts

_UNESCAPED_DOLLAR = re.compile(r"(?<!\\)\$")
_NAMED_WEIGHTS = {"normal": 400, "bold": 700}


def glyph_weight(weight: str | int | None) -> int:
    """GlyphKit's numeric weight for a ``TextStyle.weight`` (None is normal)."""
    if weight is None:
        return 400
    if isinstance(weight, str):
        return _NAMED_WEIGHTS[weight]
    return int(weight)


class TextTypesetter:
    """Lays out plain strings in the faces of one ``TextFonts``."""

    def __init__(self, fonts: TextFonts) -> None:
        self.fonts = fonts
        try:
            # GlyphKit types ``from_sources`` as its catalog base class; it returns a FontLibrary.
            self._library = cast(
                FontLibrary,
                FontLibrary.from_sources(tuple(FontSource.path(path) for path in fonts.paths)),
            )
        except GlyphKitError as exc:
            raise ConfigurationError(
                f"Cannot load text fonts {list(map(str, fonts.paths))}: {exc}"
            ) from exc
        families: list[str] = []
        for face in self._library.faces:
            if face.family not in families:
                families.append(face.family)
        self._families = tuple(families)
        self._layouts: dict[tuple[str, float, int], MathLayout] = {}

    def layout(self, text: str, size: float, weight: int) -> MathLayout:
        key = (text, size, weight)
        if key not in self._layouts:
            self._layouts[key] = self._build(text, size, weight)
        return self._layouts[key]

    def _build(self, text: str, size: float, weight: int) -> MathLayout:
        style = GlyphStyle(self._families, size, weight=weight)
        try:
            layout = self._library.layout(Paragraph((TextSpan(text, style),)))
        except GlyphKitError as exc:
            raise RenderError(f"Cannot set text {text!r} in {self._families}: {exc}") from exc
        vertices: list[tuple[float, float]] = []
        codes: list[int] = []
        for line in layout.lines:
            for run in line.runs:
                for glyph in run.glyphs:
                    outline = self._library.outline(glyph)
                    scale = run.size / outline.units_per_em
                    _append_outline(
                        outline.commands,
                        scale,
                        glyph.x + glyph.x_offset,
                        glyph.y + glyph.y_offset,
                        vertices,
                        codes,
                    )
        bounds = layout.logical_bounds
        if vertices:
            ink = Path(vertices, codes).get_extents()
            box = (
                min(bounds.x_min, float(ink.x0)),
                min(bounds.y_min, float(ink.y0)),
                max(bounds.x_max, float(ink.x1)),
                max(bounds.y_max, float(ink.y1)),
            )
            path = Path(vertices, codes)
        else:  # blank text: nothing to draw but it still takes room
            box = (bounds.x_min, bounds.y_min, bounds.x_max, bounds.y_max)
            path = Path([(0.0, 0.0)], [_MOVETO])
        return MathLayout(text, path, box)


@lru_cache(maxsize=8)
def typesetter_for(fonts: TextFonts) -> TextTypesetter:
    return TextTypesetter(fonts)


_ACTIVE: ContextVar[TextTypesetter | None] = ContextVar("mosaickit_text_typesetter", default=None)


@contextmanager
def text_typesetting(fonts: TextFonts | None) -> Iterator[None]:
    """Route plain strings through ``fonts`` while drawing; None keeps Matplotlib's text.

    Loads the fonts up front, so an unusable file raises ``ConfigurationError`` before
    anything is drawn.
    """
    token = _ACTIVE.set(None if fonts is None else typesetter_for(fonts))
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def typeset_text(text: str, size: float, weight: str | int | None) -> MathLayout | None:
    """The GlyphKit layout of ``text``, or None when Matplotlib should draw it.

    That is the case when no text fonts are active and when ``text`` has a ``$...$`` span:
    math, or text mixed with math, is the math path's business.
    """
    typesetter = _ACTIVE.get()
    if typesetter is None or _UNESCAPED_DOLLAR.search(text):
        return None
    return typesetter.layout(text, float(size), glyph_weight(weight))
