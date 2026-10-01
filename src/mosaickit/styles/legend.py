from __future__ import annotations

from dataclasses import dataclass

from mosaickit.styles.base import SparseStyle, _check_size


@dataclass(frozen=True, slots=True)
class LegendStyle(SparseStyle):
    visible: bool | None = None
    location: str | None = None
    frame: bool | None = None
    size: float | None = None

    def __post_init__(self) -> None:
        _check_size("LegendStyle.size", self.size)
