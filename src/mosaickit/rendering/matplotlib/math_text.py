"""Math text set from GlyphKit outlines when the caller chose a math font.

Without a ``MathFont`` nothing here is active and math goes to Matplotlib's
mathtext, exactly as before. With one, every label that is a single ``$...$`` span
is laid out by GlyphKit (OpenType ``MATH`` table), turned into a Matplotlib path, and
drawn as a ``Text`` subclass so label placement, window extents, and tight bounding
boxes see it like any other text. Measuring and drawing share one layout, so
the size placement reserves is the size that gets drawn.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, fields, is_dataclass, replace
from functools import lru_cache
from typing import Any, cast

import numpy as np
from glyphkit import FontLibrary, FontSource, GlyphKitError, SourceRange
from glyphkit.math import Limits, MathBox, MathStyle, Script, Sequence, Symbol, parse_math
from glyphkit.outlines import ClosePath, CubicTo, LineTo, MoveTo, QuadraticTo
from matplotlib.path import Path
from matplotlib.text import Text
from matplotlib.transforms import Affine2D, Bbox, Transform, offset_copy

from mosaickit.errors import ConfigurationError, RenderError
from mosaickit.math_font import MathFont

_MOVETO, _LINETO, _CURVE3, _CURVE4, _CLOSEPOLY = (
    int(code) for code in (Path.MOVETO, Path.LINETO, Path.CURVE3, Path.CURVE4, Path.CLOSEPOLY)
)
_UNESCAPED_DOLLAR = re.compile(r"(?<!\\)\$")
_MINUS = 0x2212
_ITALIC_CAPITAL_A = 0x1D434
_ITALIC_SMALL_A = 0x1D44E
_ITALIC_SMALL_ALPHA = 0x1D6FC
_PLANCK = 0x210E  # Mathematical Italic small h is a hole in Unicode; this is its letter


@dataclass(frozen=True, slots=True)
class MathLayout:
    """Laid-out math in points: a path with its origin at the left end of the baseline."""

    source: str
    path: Path
    box: tuple[float, float, float, float]  # x0, y0, x1, y1 around the ink and advance

    def corners(self, scale: float, rotation: float) -> np.ndarray:
        """The box corners in pixels after ``scale`` (px per pt) and ``rotation`` degrees."""
        x0, y0, x1, y1 = self.box
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return np.asarray(Affine2D().scale(scale).rotate_deg(rotation).transform(corners))

    def measure(self, scale: float, rotation: float) -> tuple[float, float]:
        """Width and height in pixels of the rotated box."""
        corners = self.corners(scale, rotation)
        span = corners.max(axis=0) - corners.min(axis=0)
        return float(span[0]), float(span[1])


def _italic(symbol: Symbol, coverage: frozenset[int]) -> Symbol:
    value = symbol.value
    if len(value) != 1 or symbol.role not in {"ordinary", "identifier"}:
        return symbol
    code = ord(value)
    if value == "h":
        target = _PLANCK
    elif "A" <= value <= "Z":
        target = _ITALIC_CAPITAL_A + code - ord("A")
    elif "a" <= value <= "z":
        target = _ITALIC_SMALL_A + code - ord("a")
    elif 0x3B1 <= code <= 0x3C9:
        target = _ITALIC_SMALL_ALPHA + code - 0x3B1
    else:
        return symbol
    return replace(symbol, value=chr(target)) if target in coverage else symbol


_RELATIONS = "=<>"
_BINARY = "+\u2212-\u00d7\u00f7"
_SPACES = (0x2005, 0x20)  # four-per-em, then the plain space


def _spaced(children: tuple[Any, ...], space: str | None) -> tuple[Any, ...]:
    """Add a space around relations and binary operators; GlyphKit sets atoms back to back."""
    if space is None:
        return children
    result: list[Any] = []
    for child in children:
        operator = isinstance(child, Symbol) and child.role == "operator"
        value = child.value if isinstance(child, Symbol) else ""
        before = result[-1] if result else None
        binary = (
            value in _BINARY
            and before is not None
            and not (isinstance(before, Symbol) and before.role == "operator" or _opens(before))
        )
        if operator and (value in _RELATIONS or binary):
            gap = Symbol(space, child.source_range)
            result.extend((gap, child, gap))
        else:
            result.append(child)
    return tuple(result)


def _opens(node: Any) -> bool:
    return isinstance(node, Symbol) and node.value in "([{,"


def _typeset_symbols(node: Any, coverage: frozenset[int], italic: bool, tight: bool = False) -> Any:
    """Set letters in the Mathematical Italic alphabet, ``-`` as a true minus, and
    operators with space around them (not inside scripts, where TeX keeps them tight)."""
    space = next((chr(c) for c in _SPACES if c in coverage), None)

    def walk(value: Any, tight: bool) -> Any:
        if isinstance(value, Symbol):
            if value.value == "-" and value.role == "operator" and _MINUS in coverage:
                return replace(value, value=chr(_MINUS))
            return _italic(value, coverage) if italic else value
        if isinstance(value, tuple):
            return tuple(walk(item, tight) for item in value)
        if not is_dataclass(value) or isinstance(value, (type, SourceRange)):
            return value
        scripts = isinstance(value, (Script, Limits))
        changes = {}
        for slot in fields(value):
            part = getattr(value, slot.name)
            inside = tight or (
                scripts and slot.name in {"subscript", "superscript", "lower", "upper"}
            )
            changes[slot.name] = walk(part, inside)
        if isinstance(value, Sequence) and not tight:
            changes["children"] = _spaced(changes["children"], space)
        return replace(value, **changes)

    return walk(node, tight)


class MathTypesetter:
    """Lays out TeX-like formulas in one caller-chosen math font."""

    def __init__(self, font: MathFont) -> None:
        self.font = font
        try:
            # GlyphKit types ``from_sources`` as its catalog base class; it returns a FontLibrary.
            self._library = cast(
                FontLibrary, FontLibrary.from_sources((FontSource.path(font.path),))
            )
        except GlyphKitError as exc:
            raise ConfigurationError(f"Cannot load math font {font.path}: {exc}") from exc
        self._face = next((face for face in self._library.faces if face.has_math), None)
        if self._face is None:
            raise ConfigurationError(
                f"Math font {font.path} has no OpenType MATH table; "
                "use a math font such as STIX Two Math, Libertinus Math, or Fira Math"
            )
        self._layouts: dict[tuple[str, float], MathLayout] = {}

    def layout(self, source: str, size: float) -> MathLayout:
        key = (source, size)
        if key not in self._layouts:
            self._layouts[key] = self._build(source, size)
        return self._layouts[key]

    def _build(self, source: str, size: float) -> MathLayout:
        assert self._face is not None
        try:
            tree = _typeset_symbols(parse_math(source), self._face.coverage, self.font.italic)
            box = self._library.layout_math(tree, style=MathStyle(size, (self._face.family,)))
        except GlyphKitError as exc:
            raise RenderError(f"Cannot set math {source!r} in {self._face.family}: {exc}") from exc
        vertices: list[tuple[float, float]] = []
        codes: list[int] = []
        self._collect(box, 0.0, 0.0, vertices, codes)
        if not vertices:
            raise RenderError(f"Math {source!r} has nothing to draw")
        path = Path(vertices, codes)
        ink = path.get_extents()
        return MathLayout(
            f"${source}$",
            path,
            (
                min(0.0, float(ink.x0)),
                float(ink.y0),
                max(box.bounds.x_max, float(ink.x1)),
                float(ink.y1),
            ),
        )

    def _collect(
        self,
        box: MathBox,
        dx: float,
        dy: float,
        vertices: list[tuple[float, float]],
        codes: list[int],
    ) -> None:
        x, y = dx + box.origin[0], dy + box.origin[1]
        if box.text_layout is not None:
            for line in box.text_layout.lines:
                for run in line.runs:
                    for glyph in run.glyphs:
                        outline = self._library.outline(glyph)
                        scale = run.size / outline.units_per_em
                        gx, gy = x + glyph.x, y + line.baseline + glyph.y
                        _append_outline(outline.commands, scale, gx, gy, vertices, codes)
        for rule in box.rules:
            (x0, y0), (x1, y1) = rule.start, rule.end
            half = rule.thickness / 2
            corners = [(x0, y0 - half), (x1, y0 - half), (x1, y1 + half), (x0, y1 + half)]
            vertices.extend((x + cx, y + cy) for cx, cy in corners)
            codes.extend([_MOVETO, _LINETO, _LINETO, _LINETO])
            vertices.append(vertices[-4])
            codes.append(_CLOSEPOLY)
        for child in box.children:
            self._collect(child, x, y, vertices, codes)


def _append_outline(
    commands: Any,
    scale: float,
    dx: float,
    dy: float,
    vertices: list[tuple[float, float]],
    codes: list[int],
) -> None:
    start = (dx, dy)

    def place(point: tuple[float, float]) -> tuple[float, float]:
        return (dx + point[0] * scale, dy + point[1] * scale)

    for command in commands:
        if isinstance(command, MoveTo):
            start = place(command.point)
            vertices.append(start)
            codes.append(_MOVETO)
        elif isinstance(command, LineTo):
            vertices.append(place(command.point))
            codes.append(_LINETO)
        elif isinstance(command, QuadraticTo):
            vertices.extend((place(command.control), place(command.point)))
            codes.extend([_CURVE3, _CURVE3])
        elif isinstance(command, CubicTo):
            vertices.extend(
                (place(command.control1), place(command.control2), place(command.point))
            )
            codes.extend([_CURVE4] * 3)
        elif isinstance(command, ClosePath):
            vertices.append(start)
            codes.append(_CLOSEPOLY)


@lru_cache(maxsize=8)
def typesetter_for(font: MathFont) -> MathTypesetter:
    return MathTypesetter(font)


_ACTIVE: ContextVar[MathTypesetter | None] = ContextVar("mosaickit_math_typesetter", default=None)


@contextmanager
def math_typesetting(font: MathFont | None) -> Iterator[None]:
    """Route whole-string ``$...$`` math through ``font`` while drawing; None keeps mathtext.

    Loads the font up front, so an unusable font raises ``ConfigurationError`` before
    anything is drawn.
    """
    token = _ACTIVE.set(None if font is None else typesetter_for(font))
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def _formula(text: str) -> str | None:
    """The TeX inside ``text`` when all of it is one ``$...$`` span, else None."""
    if len(text) < 3 or not (text.startswith("$") and text.endswith("$")):
        return None
    inner = text[1:-1]
    if _UNESCAPED_DOLLAR.search(inner) or not inner.strip():
        return None
    return inner


def typeset(text: str, size: float) -> MathLayout | None:
    """The GlyphKit layout of ``text``, or None when it should go through mathtext.

    That is the case when no math font is active and when ``text`` is not purely one
    math span (text mixed with ``$...$`` stays with Matplotlib).
    """
    typesetter = _ACTIVE.get()
    formula = _formula(text)
    if typesetter is None or formula is None:
        return None
    return typesetter.layout(formula, float(size))


class MathText(Text):  # type: ignore[misc]
    """A ``Text`` whose glyphs are outlines drawn at the text's position and alignment."""

    def __init__(self, x: float, y: float, layout: MathLayout, **kwargs: Any) -> None:
        super().__init__(x, y, layout.source, **kwargs)
        self._math = layout

    def _placement(self, dpi: float | None = None) -> tuple[Transform, Bbox]:
        scale = (self.figure.dpi if dpi is None else dpi) / 72
        rotation = float(self.get_rotation())
        corners = self._math.corners(scale, rotation)
        (left, bottom), (right, top) = corners.min(axis=0), corners.max(axis=0)
        horizontal = {"left": left, "right": right}.get(
            self.get_horizontalalignment(), (left + right) / 2
        )
        vertical = {"top": top, "bottom": bottom, "baseline": 0.0}.get(
            self.get_verticalalignment(), (bottom + top) / 2
        )
        x, y = self.get_transform().transform(self.get_unitless_position())
        move = Affine2D().translate(x - horizontal, y - vertical)
        return Affine2D().scale(scale).rotate_deg(rotation) + move, Bbox.from_extents(
            left + x - horizontal, bottom + y - vertical, right + x - horizontal, top + y - vertical
        )

    def get_window_extent(self, renderer: Any = None, dpi: float | None = None) -> Bbox:
        if not self.get_visible() or self.figure is None:
            return Bbox.unit()
        return self._placement(dpi)[1]

    def draw(self, renderer: Any) -> None:
        if not self.get_visible():
            return
        transform, _ = self._placement()
        color = self.get_color()
        renderer.open_group("text", self.get_gid())
        gc = renderer.new_gc()
        gc.set_foreground(color, isRGBA=True)
        gc.set_linewidth(0)
        gc.set_clip_rectangle(None)
        gc.set_gid(self.get_gid())
        renderer.draw_path(gc, self._math.path, transform, rgbFace=color)
        gc.restore()
        renderer.close_group("text")
        self.stale = False


def draw_math(
    ax: Any,
    layout: MathLayout,
    xy: tuple[float, float],
    *,
    color: Any,
    rotation: float,
    zorder: float,
    align: tuple[str, str],
    offset_pt: tuple[float, float] | None = None,
    gid: str | None = None,
) -> MathText:
    """Add ``layout`` at data point ``xy`` (moved by ``offset_pt`` points) and return it."""
    transform = ax.transData
    if offset_pt is not None:
        transform = offset_copy(
            ax.transData, fig=ax.figure, x=offset_pt[0], y=offset_pt[1], units="points"
        )
    artist = MathText(
        xy[0],
        xy[1],
        layout,
        color=color,
        rotation=rotation,
        horizontalalignment=align[0],
        verticalalignment=align[1],
        transform=transform,
        zorder=zorder,
        clip_on=False,
    )
    if gid is not None:
        artist.set_gid(gid)
    ax.add_artist(artist)
    return artist


__all__ = [
    "MathLayout",
    "MathText",
    "MathTypesetter",
    "draw_math",
    "math_typesetting",
    "typeset",
    "typesetter_for",
]
