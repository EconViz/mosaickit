from __future__ import annotations

from dataclasses import dataclass

from mosaickit.colors import Color
from mosaickit.styles.base import SparseStyle, _check_size, _coerce_color, check_opacity


@dataclass(frozen=True, slots=True)
class Marker(SparseStyle):
    color: Color | str | None = None
    size: float | None = None
    shape: str | None = None
    opacity: float | None = None
    edge_color: Color | str | None = None
    edge_width: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "color", _coerce_color(self.color))
        object.__setattr__(self, "edge_color", _coerce_color(self.edge_color))
        _check_size("Marker.size", self.size)
        _check_size("Marker.edge_width", self.edge_width)
        check_opacity("Marker", self.opacity)
