"""The fonts plain text is set in."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mosaickit.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class TextFonts:
    """Caller-chosen font files for text, selected and laid out by GlyphKit.

    List every face the figures need, for example a regular and a bold file, or one
    variable font. A text style's ``weight`` (an integer from 1 to 1000, ``"normal"``
    or ``"bold"``) picks the nearest listed face; the order of the files is the order
    in which a face is tried for a character the first one lacks. MosaicKit never
    searches the system for fonts: pass the paths of the files you want.

    Without ``TextFonts`` text is drawn by Matplotlib with its default face, as before.
    """

    paths: tuple[Path, ...]

    def __post_init__(self) -> None:
        paths: Any = self.paths
        if isinstance(paths, (str, os.PathLike)):
            paths = (paths,)
        if not isinstance(paths, Iterable) or isinstance(paths, (bytes, Mapping)):
            raise ConfigurationError("TextFonts.paths must be file paths")
        checked = []
        for value in paths:
            if not isinstance(value, (str, os.PathLike)):
                raise ConfigurationError("TextFonts.paths must be file paths")
            path = Path(value).expanduser()
            if not path.is_file():
                raise ConfigurationError(f"TextFonts.paths is not a font file: {path}")
            checked.append(path)
        if not checked:
            raise ConfigurationError("TextFonts needs at least one font file")
        object.__setattr__(self, "paths", tuple(checked))
