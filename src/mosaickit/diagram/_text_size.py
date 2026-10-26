"""Size estimate of a TeX label: stacked fractions, large delimiters and scripts."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

Point = tuple[float, float]


@dataclass(frozen=True, slots=True)
class TextSizeFactors:
    """How stacked TeX constructs change the size of a label, in glyphs and lines.

    A glyph is ``char_width`` em wide and a line is ``line_height`` em high.
    """

    script_scale: float = 0.7
    """Size of a sub/superscript and of the parts of an inline ``\\frac`` against the text."""
    script_rise: float = 0.2
    """Lines a sub/superscript adds to the height of the line it sits on."""
    fraction_padding: float = 0.5
    """Glyphs a fraction adds to the width of its wider part, for the bar and its margins."""
    display_scale: float = 1.0
    """Size of the parts of a ``\\dfrac`` against the text."""
    delimiter_width: float = 1.0
    """Glyphs of a delimiter that fits on one line."""
    large_delimiter_width: float = 1.2
    """Glyphs of a ``\\left``/``\\right`` delimiter taller than one line."""


DEFAULT_TEXT_SIZE_FACTORS = TextSizeFactors()
"""The factors :func:`~mosaickit.diagram.estimate_text_size` uses unless given others."""

_FRACTIONS = {"frac": "script_scale", "dfrac": "display_scale"}
_SCRIPTS = "^_"
_SILENT = ",{}"  # after a backslash these draw nothing, like the markup characters
_MARKUP = "$,"
_SPACING = {",", ";", ":", "!", " "}  # backslash spacing commands draw nothing
_COMMAND = re.compile(r"\\([A-Za-z]+)")


class _Parser:
    def __init__(self, text: str, skip: frozenset[str], factors: TextSizeFactors) -> None:
        self.text = text
        self.skip = skip
        self.factors = factors
        self.pos = 0

    def sequence(self, until_right: bool = False) -> Point:
        """Width in glyphs and height in lines up to the end, a closing brace or ``\\right``."""
        width, height = 0.0, 1.0
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char == "}" or (until_right and self._at("right")):
                break
            part = self._item()
            width += part[0]
            height = max(height, part[1])
        return width, height

    def _at(self, name: str) -> bool:
        match = _COMMAND.match(self.text, self.pos)
        return match is not None and match.group(1) == name and name not in self.skip

    def _argument(self) -> Point:
        """A braced group or the single token after a script mark or fraction part."""
        if self.pos < len(self.text) and self.text[self.pos] == "{":
            self.pos += 1
            part = self.sequence()
            self.pos += 1
            return part
        return self._item() if self.pos < len(self.text) else (0.0, 1.0)

    def _item(self) -> Point:
        char = self.text[self.pos]
        if char == "{":
            return self._argument()
        if char in _SCRIPTS:
            self.pos += 1
            width, _ = self._argument()
            f = self.factors
            return width * f.script_scale, 1.0 + f.script_rise
        if char == "\\":
            return self._command()
        self.pos += 1
        return (0.0, 1.0) if char in _MARKUP else (1.0, 1.0)

    def _command(self) -> Point:
        match = _COMMAND.match(self.text, self.pos)
        if not match:  # a backslash and one symbol: spacing and brace escapes draw nothing
            symbol = self.text[self.pos + 1 : self.pos + 2]
            self.pos += 2
            return (0.0, 1.0) if symbol in _SPACING or symbol in _SILENT else (1.0, 1.0)
        name = match.group(1)
        self.pos = match.end()
        if name in self.skip:
            return 0.0, 1.0
        if name in _FRACTIONS:
            return self._fraction(getattr(self.factors, _FRACTIONS[name]))
        if name == "left":
            return self._delimited()
        return 1.0, 1.0

    def _fraction(self, scale: float) -> Point:
        (nw, nh), (dw, dh) = self._argument(), self._argument()
        width = max(nw, dw) * scale + self.factors.fraction_padding
        return width, (nh + dh) * scale

    def _delimiter(self) -> None:
        match = _COMMAND.match(self.text, self.pos)
        self.pos = match.end() if match else self.pos + 1

    def _delimited(self) -> Point:
        self._delimiter()
        width, height = self.sequence(until_right=True)
        if self._at("right"):
            self._delimiter()
            self._delimiter()
        f = self.factors
        edge = f.large_delimiter_width if height > 1.0 else f.delimiter_width
        return width + 2 * edge, height


def estimate_text_size(
    label: str,
    font_size: float,
    *,
    char_width: float = 0.8,
    line_height: float = 1.25,
    strip_commands: Iterable[str] = (),
    factors: TextSizeFactors = DEFAULT_TEXT_SIZE_FACTORS,
) -> Point:
    """Estimated ``(width, height)`` in points of ``label`` set at ``font_size`` points.

    Markup characters (``$ \\ { } ,``) count for nothing and every TeX command counts as one
    glyph, except the commands named in ``strip_commands`` (without the backslash, for example
    :data:`~mosaickit.diagram.TEX_LAYOUT_COMMANDS`), which count for nothing and leave their
    arguments as plain text. Stacked constructs take room as in the typeset label: ``\\frac`` and
    ``\\dfrac`` put the numerator over the denominator, ``\\left``/``\\right`` delimiters are as
    high as what they enclose, and ``^``/``_`` arguments are smaller and raise the line, all by
    ``factors``. ``char_width`` and ``line_height`` are in em. The defaults are the estimate
    :class:`~mosaickit.diagram.Diagram` uses.
    """
    parser = _Parser(label, frozenset(strip_commands), factors)
    width, height = 0.0, 1.0
    while parser.pos < len(label):
        w, h = parser.sequence()
        width, height = width + w, max(height, h)
        parser.pos += 1  # a stray closing brace
    return char_width * font_size * width, line_height * font_size * height
