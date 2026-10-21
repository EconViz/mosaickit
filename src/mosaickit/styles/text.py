from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from mosaickit.colors import Color
from mosaickit.errors import ConfigurationError
from mosaickit.styles.base import SparseStyle, _check_size, _coerce_color, check_opacity

_NAMED_WEIGHTS = ("normal", "bold")


@dataclass(frozen=True, slots=True)
class TextStyle(SparseStyle):
    color: Color | str | None = None
    size: float | None = None
    weight: str | int | None = None
    opacity: float | None = None
    rotation: float | None = None
    font: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "color", _coerce_color(self.color))
        _check_size("TextStyle.size", self.size)
        check_opacity("TextStyle", self.opacity)
        if self.rotation is not None and not math.isfinite(self.rotation):
            raise ConfigurationError("TextStyle.rotation must be finite")
        _check_weight(self.weight)
        _check_font(self.font)


def _check_weight(weight: Any) -> None:
    """``weight`` is ``"normal"``, ``"bold"`` or an integer from 1 to 1000 (GlyphKit's scale)."""
    if weight is None or weight in _NAMED_WEIGHTS and isinstance(weight, str):
        return
    if isinstance(weight, int) and not isinstance(weight, bool) and 1 <= weight <= 1000:
        return
    raise ConfigurationError(
        f"TextStyle.weight must be 'normal', 'bold' or an integer from 1 to 1000, got {weight!r}"
    )


def _check_font(font: Any) -> None:
    """``font`` is a generic font name: ``"sans"``, ``"serif"`` or ``"mono"``."""
    if font is None or font in ("sans", "serif", "mono") and isinstance(font, str):
        return
    raise ConfigurationError(f"TextStyle.font must be 'sans', 'serif' or 'mono', got {font!r}")
