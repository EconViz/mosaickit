"""Shared sparse merge and style validation."""

from __future__ import annotations

import math
from dataclasses import fields, is_dataclass, replace
from typing import TypeVar

from mosaickit.colors import Color
from mosaickit.errors import ConfigurationError

S = TypeVar("S", bound="SparseStyle")


class SparseStyle:
    def merged_over(self: S, base: S) -> S:
        if type(self) is not type(base):
            raise TypeError("Sparse styles must have the same type")
        if not is_dataclass(self) or not is_dataclass(base):
            raise TypeError("SparseStyle requires frozen dataclasses")
        updates = {f.name: v for f in fields(self) if (v := getattr(self, f.name)) is not None}
        return replace(base, **updates)


def _coerce_color(value: Color | str | None) -> Color | str | None:
    """Parse ``#hex`` into a Color; keep any other string as a palette name.

    Names are resolved against the active palette when a render plan is built.
    """
    if value is None or isinstance(value, Color):
        return value
    if not isinstance(value, str) or not value:
        raise ConfigurationError("Color must be a Color, a #hex string, or a palette name")
    return Color.from_hex(value) if value.startswith("#") else value


def check_opacity(name: str, value: float | None) -> None:
    if value is not None and (not math.isfinite(value) or not 0 <= value <= 1):
        raise ConfigurationError(f"{name}.opacity must be finite and in [0, 1]")


def _check_size(name: str, value: float | None) -> None:
    if value is not None and (not math.isfinite(value) or value < 0):
        raise ConfigurationError(f"{name} must be finite and non-negative")
