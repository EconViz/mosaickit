"""Finite increasing intervals shared by viewports and axes."""

from __future__ import annotations

import math
from dataclasses import dataclass

from mosaickit.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class Interval:
    lo: float
    hi: float

    def __post_init__(self) -> None:
        if not (math.isfinite(self.lo) and math.isfinite(self.hi)):
            raise ConfigurationError("Interval bounds must be finite")
        if not self.lo < self.hi:
            raise ConfigurationError("Interval requires lo < hi")
