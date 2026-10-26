"""Renderer-neutral spacing controls for canvas grids."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

from mosaickit.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class GridSpacing:
    """Proportional spacing around and between cells in a :class:`CanvasGrid`.

    ``column_gap`` and ``row_gap`` are fractions of a cell's width and height.
    ``outer`` is the symmetric margin on every side as a fraction of the whole
    grid. Leaving a value as ``None`` preserves the renderer's existing default.
    """

    column_gap: float | None = None
    row_gap: float | None = None
    outer: float | None = None

    def __post_init__(self) -> None:
        for name in ("column_gap", "row_gap", "outer"):
            value = getattr(self, name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, Real):
                raise ConfigurationError(f"GridSpacing.{name} must be a finite number")
            number = float(value)
            if not math.isfinite(number):
                raise ConfigurationError(f"GridSpacing.{name} must be a finite number")
            if number < 0:
                raise ConfigurationError(f"GridSpacing.{name} cannot be negative")
            if name == "outer" and number >= 0.5:
                raise ConfigurationError("GridSpacing.outer must be less than 0.5")
            object.__setattr__(self, name, number)
