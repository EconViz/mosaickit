from __future__ import annotations

import math
from dataclasses import dataclass

from mosaickit.colors import Color
from mosaickit.errors import ConfigurationError
from mosaickit.styles.base import SparseStyle, _check_size, _coerce_color, check_opacity


@dataclass(frozen=True, slots=True)
class TextStyle(SparseStyle):
    color: Color | str | None = None
    size: float | None = None
    family: str | None = None
    weight: str | None = None
    opacity: float | None = None
    rotation: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "color", _coerce_color(self.color))
        _check_size("TextStyle.size", self.size)
        check_opacity("TextStyle", self.opacity)
        if self.rotation is not None and not math.isfinite(self.rotation):
            raise ConfigurationError("TextStyle.rotation must be finite")
