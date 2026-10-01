from __future__ import annotations

from dataclasses import dataclass

from mosaickit.colors import Color
from mosaickit.styles.base import SparseStyle, _coerce_color, check_opacity


@dataclass(frozen=True, slots=True)
class Fill(SparseStyle):
    color: Color | str | None = None
    opacity: float | None = None
    hatch: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "color", _coerce_color(self.color))
        check_opacity("Fill", self.opacity)
