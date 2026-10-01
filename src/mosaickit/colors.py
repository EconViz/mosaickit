"""Immutable, backend-independent RGBA colors."""

from __future__ import annotations

import math
import string
from dataclasses import dataclass

from mosaickit.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class Color:
    red: float
    green: float
    blue: float
    alpha: float = 1.0

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in self.channels):
            raise ConfigurationError("Color channels must be finite and in [0, 1]")

    @property
    def channels(self) -> tuple[float, float, float, float]:
        return self.red, self.green, self.blue, self.alpha

    @classmethod
    def from_channels(cls, red: float, green: float, blue: float, alpha: float = 1) -> Color:
        return cls(red, green, blue, alpha)

    @classmethod
    def from_hex(cls, value: str) -> Color:
        if not isinstance(value, str) or not value.startswith("#"):
            raise ConfigurationError("Color must be #RGB, #RRGGBB, or #RRGGBBAA")
        digits = value[1:]
        if len(digits) == 3:
            digits = "".join(c * 2 for c in digits)
        if len(digits) not in (6, 8) or any(char not in string.hexdigits for char in digits):
            raise ConfigurationError(f"Invalid hex color: {value!r}")
        try:
            channels = [int(digits[i : i + 2], 16) / 255 for i in range(0, len(digits), 2)]
        except ValueError as exc:
            raise ConfigurationError(f"Invalid hex color: {value!r}") from exc
        return cls(*channels)

    def to_hex(self, *, include_alpha: bool | None = None) -> str:
        alpha = self.alpha != 1 if include_alpha is None else include_alpha
        return "#" + "".join(f"{round(v * 255):02X}" for v in self.channels[: 4 if alpha else 3])


TRANSPARENT = Color(0, 0, 0, 0)
