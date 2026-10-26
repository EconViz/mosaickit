"""Plain text set from GlyphKit outlines.

The counterpart of ``math_text`` for ordinary strings. Every string without ``$...$`` math is
laid out by GlyphKit in one of three generic fonts (sans, serif, mono), turned into a path, and
drawn as the same ``MathText`` artist the math path uses, so label placement, window extents and
tight bounding boxes see it like any other text, and measuring and drawing share one layout.

The fonts are DejaVu Sans, Serif and Sans Mono from the files Matplotlib installs, and a
``TextFonts`` replaces any of the three. Text mixed with ``$...$`` math is left to Matplotlib.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path as FilePath
from typing import Any, cast

import matplotlib
from glyphkit import FontLibrary, FontSource, GlyphKitError, Paragraph, TextSpan
from glyphkit import TextStyle as GlyphStyle
from matplotlib.path import Path

from mosaickit.errors import ConfigurationError, RenderError
from mosaickit.rendering.matplotlib.math_text import (
    _MOVETO,
    InkBox,
    MathLayout,
    _append_outline,
    glyph_ink,
    union_ink,
)
from mosaickit.text_fonts import GENERIC_FONTS, TextFonts

_UNESCAPED_DOLLAR = re.compile(r"(?<!\\)\$")
_NAMED_WEIGHTS = {"normal": 400, "bold": 700}


def glyph_weight(weight: str | int | None) -> int:
    """GlyphKit's numeric weight for a ``TextStyle.weight`` (None is normal)."""
    if weight is None:
        return 400
    if isinstance(weight, str):
        return _NAMED_WEIGHTS[weight]
    return int(weight)


_DEFAULT_FILES = {
    "sans": ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    "serif": ("DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf"),
    "mono": ("DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf"),
}


def default_files(slot: str) -> tuple[FilePath, ...]:
    """The default font files of a generic font, from the fonts Matplotlib installs."""
    directory = FilePath(matplotlib.get_data_path()) / "fonts" / "ttf"
    return tuple(directory / name for name in _DEFAULT_FILES[slot])


class TextTypesetter:
    """Lays out plain strings in the generic fonts of one ``TextFonts``."""

    def __init__(self, fonts: TextFonts) -> None:
        self.fonts = fonts
        self._libraries: dict[str, tuple[FontLibrary, tuple[str, ...]]] = {}
        self._layouts: dict[tuple[str, float, int, str], MathLayout] = {}
        self._ink: dict[Any, InkBox | None] = {}
        for slot in GENERIC_FONTS:
            # Files you gave load now, so an unusable one fails before drawing; the defaults are
            # Matplotlib's own files and load when a string first uses the slot.
            if getattr(self.fonts, slot):
                self._library(slot)

    def _library(self, slot: str) -> tuple[FontLibrary, tuple[str, ...]]:
        if slot not in self._libraries:
            files = getattr(self.fonts, slot) or default_files(slot)
            try:
                # GlyphKit types ``from_sources`` as its catalog base; it returns a FontLibrary.
                library = cast(
                    FontLibrary, FontLibrary.from_sources(tuple(FontSource.path(f) for f in files))
                )
            except GlyphKitError as exc:
                raise ConfigurationError(
                    f"Cannot load {slot} font {[str(f) for f in files]}: {exc}"
                ) from exc
            families: list[str] = []
            for face in library.faces:
                if face.family not in families:
                    families.append(face.family)
            self._libraries[slot] = (library, tuple(families))
        return self._libraries[slot]

    def layout(self, text: str, size: float, weight: int, slot: str = "sans") -> MathLayout:
        key = (text, size, weight, slot)
        if key not in self._layouts:
            self._layouts[key] = self._build(text, size, weight, slot)
        return self._layouts[key]

    def _build(self, text: str, size: float, weight: int, slot: str) -> MathLayout:
        library, families = self._library(slot)
        style = GlyphStyle(families, size, weight=weight)
        try:
            layout = library.layout(Paragraph((TextSpan(text, style),)))
        except GlyphKitError as exc:
            raise RenderError(f"Cannot set text {text!r} in the {slot} font: {exc}") from exc
        vertices: list[tuple[float, float]] = []
        codes: list[int] = []
        boxes: list[InkBox] = []
        for line in layout.lines:
            for run in line.runs:
                for glyph in run.glyphs:
                    outline = library.outline(glyph)
                    scale = run.size / outline.units_per_em
                    gx, gy = glyph.x + glyph.x_offset, glyph.y + glyph.y_offset
                    _append_outline(outline.commands, scale, gx, gy, vertices, codes)
                    ink = glyph_ink(self._ink, glyph, outline.commands, scale, gx, gy)
                    if ink is not None:
                        boxes.append(ink)
        bounds = layout.logical_bounds
        if vertices:
            path = Path(vertices, codes)
            x0, y0, x1, y1 = union_ink(boxes)
            box = (
                min(bounds.x_min, float(x0)),
                min(bounds.y_min, float(y0)),
                max(bounds.x_max, float(x1)),
                max(bounds.y_max, float(y1)),
            )
        else:  # blank text: nothing to draw but it still takes room
            box = (bounds.x_min, bounds.y_min, bounds.x_max, bounds.y_max)
            path = Path([(0.0, 0.0)], [_MOVETO])
        return MathLayout(text, path, box)


def typesetter_for(fonts: TextFonts) -> TextTypesetter:
    """The typesetter for ``fonts``, shared by every ``TextFonts`` naming the same files.

    The cache is keyed by the files' real paths, so the same fonts reached through
    different symbolic links (one link per sandboxed workspace, say) are parsed once.
    """
    return _typesetter(*(_real(getattr(fonts, slot)) for slot in GENERIC_FONTS))


def _real(files: tuple[FilePath, ...] | None) -> tuple[FilePath, ...] | None:
    return None if files is None else tuple(path.resolve() for path in files)


@lru_cache(maxsize=8)
def _typesetter(
    sans: tuple[FilePath, ...] | None,
    serif: tuple[FilePath, ...] | None,
    mono: tuple[FilePath, ...] | None,
) -> TextTypesetter:
    return TextTypesetter(TextFonts(sans=sans, serif=serif, mono=mono))


_ACTIVE: ContextVar[TextTypesetter | None] = ContextVar("mosaickit_text_typesetter", default=None)


@contextmanager
def text_typesetting(fonts: TextFonts | None) -> Iterator[None]:
    """Set plain text in ``fonts`` while drawing; None means the default fonts.

    Loads the fonts up front, so an unusable file raises ``ConfigurationError`` before
    anything is drawn.
    """
    token = _ACTIVE.set(typesetter_for(fonts if fonts is not None else TextFonts()))
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def configured_file(slot: str) -> FilePath | None:
    """The first file you gave for the generic font ``slot`` while drawing, if any.

    Matplotlib draws the text GlyphKit does not (text mixed with ``$...$`` math); it needs
    a file with the characters, which its own fonts may lack (Chinese, for example).
    """
    typesetter = _ACTIVE.get()
    files = getattr(typesetter.fonts, slot, None) if typesetter is not None else None
    return FilePath(files[0]) if files else None


def typeset_text(text: str, style) -> MathLayout | None:
    """The GlyphKit layout of ``text`` in ``style``, or None when Matplotlib should draw it.

    That is the case outside ``text_typesetting``, when ``text`` has a ``$...$`` span (math,
    or text mixed with math, is the math path's business).
    """
    typesetter = _ACTIVE.get()
    if typesetter is None or _UNESCAPED_DOLLAR.search(text):
        return None
    return typesetter.layout(
        text, float(style.size), glyph_weight(style.weight), style.font or "sans"
    )
