from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mosaickit.colors import Color
from mosaickit.styles.arrow import ArrowStyle
from mosaickit.styles.base import SparseStyle, _check_size, _coerce_color, check_opacity


class DashStyle(str, Enum):
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"
    DASHDOT = "dashdot"


@dataclass(frozen=True, slots=True)
class Stroke(SparseStyle):
    color: Color | str | None = None
    width: float | None = None
    dash: DashStyle | None = None
    arrow: ArrowStyle | None = None
    opacity: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "color", _coerce_color(self.color))
        if self.dash is not None:
            object.__setattr__(self, "dash", DashStyle(self.dash))
        if self.arrow is not None:
            object.__setattr__(self, "arrow", ArrowStyle(self.arrow))
        _check_size("Stroke.width", self.width)
        check_opacity("Stroke", self.opacity)
