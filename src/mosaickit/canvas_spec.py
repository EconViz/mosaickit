"""Physical and coordinate dimensions of a diagram."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

from mosaickit.errors import ConfigurationError
from mosaickit.interval import Interval


@dataclass(frozen=True, slots=True)
class CanvasSpec:
    x_range: tuple[float, float] = (0.0, 10.0)
    y_range: tuple[float, float] = (0.0, 10.0)
    width: float = 6.0
    height: float = 6.0
    dpi: int = 300
    x_label: str = "X"
    y_label: str = "Y"
    title: str | None = None

    def __post_init__(self) -> None:
        for name in ("x_range", "y_range"):
            value = getattr(self, name)
            try:
                interval = Interval(*value)
            except (TypeError, ValueError) as exc:
                raise ConfigurationError(f"CanvasSpec.{name}: {exc}") from exc
            object.__setattr__(self, name, (interval.lo, interval.hi))
        for name in ("width", "height"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ConfigurationError(f"CanvasSpec.{name} must be positive and finite")
        if isinstance(self.dpi, bool) or not isinstance(self.dpi, int) or not 1 <= self.dpi <= 1200:
            raise ConfigurationError("CanvasSpec.dpi must be an integer in [1, 1200]")

    @property
    def x_min(self) -> float:
        return self.x_range[0]

    @property
    def x_max(self) -> float:
        return self.x_range[1]

    @property
    def y_min(self) -> float:
        return self.y_range[0]

    @property
    def y_max(self) -> float:
        return self.y_range[1]

    def replace(self, **changes: Any) -> CanvasSpec:
        return replace(self, **changes)
