"""The font math text is set in."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mosaickit.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class MathFont:
    """A caller-chosen font file for math text.

    The file must be an OpenType font with a ``MATH`` table (for example STIX Two
    Math, Libertinus Math, or Fira Math). MosaicKit never searches the system for
    fonts: pass the path of the file you want.

    ``italic`` sets single Latin and lowercase Greek letters in the font's
    Mathematical Italic alphabet, as TeX does; digits, operators, and capital Greek
    letters stay upright. Turn it off for a font that should stay upright. A letter
    the font has no italic form for also stays upright.
    """

    path: Path
    italic: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.path, (str, os.PathLike)):
            raise ConfigurationError("MathFont.path must be a file path")
        path = Path(self.path).expanduser()
        if not path.is_file():
            raise ConfigurationError(f"MathFont.path is not a font file: {path}")
        object.__setattr__(self, "path", path)
        if not isinstance(self.italic, bool):
            raise ConfigurationError("MathFont.italic must be a bool")
