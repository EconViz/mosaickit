"""The fonts plain text is set in: three generic slots, each with a default."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mosaickit.errors import ConfigurationError

GENERIC_FONTS = ("sans", "serif", "mono")
"""The values of ``TextStyle.font``."""


def _files(slot: str, value: Any) -> tuple[Path, ...] | None:
    if value is None:
        return None
    if isinstance(value, (str, os.PathLike)):
        value = (value,)
    if not isinstance(value, Iterable) or isinstance(value, (bytes, Mapping)):
        raise ConfigurationError(f"TextFonts.{slot} must be a font file or a list of font files")
    checked = []
    for item in value:
        if not isinstance(item, (str, os.PathLike)):
            raise ConfigurationError(
                f"TextFonts.{slot} must be a font file or a list of font files"
            )
        path = Path(item).expanduser()
        if not path.is_file():
            raise ConfigurationError(f"TextFonts.{slot} is not a font file: {path}")
        checked.append(path)
    if not checked:
        raise ConfigurationError(f"TextFonts.{slot} needs at least one font file")
    return tuple(checked)


@dataclass(frozen=True, slots=True)
class TextFonts:
    """Font files for the three generic fonts, selected and laid out by GlyphKit.

    ``TextStyle.font`` names a generic font (``"sans"``, ``"serif"`` or ``"mono"``). Each
    slot you pass here replaces that generic font; the ones you leave out keep MosaicKit's
    defaults, DejaVu Sans, DejaVu Serif and DejaVu Sans Mono, which the Matplotlib
    renderer takes from the files Matplotlib installs.

    A slot takes one font file or a list. List every face it needs, for example a regular
    and a bold file, or one variable font. A text style's ``weight`` (an integer from 1 to
    1000, ``"normal"`` or ``"bold"``) picks the nearest listed face; the order of the files
    is the order a face is tried for a character the first one lacks. MosaicKit never
    searches the system for fonts: pass the paths of the files you want.
    """

    sans: tuple[Path, ...] | None = None
    serif: tuple[Path, ...] | None = None
    mono: tuple[Path, ...] | None = None

    def __post_init__(self) -> None:
        for slot in GENERIC_FONTS:
            object.__setattr__(self, slot, _files(slot, getattr(self, slot)))

    @property
    def paths(self) -> tuple[Path, ...]:
        """The sans files you gave (``TextFonts(paths)`` of 0.9.0); empty for the default."""
        return self.sans or ()
