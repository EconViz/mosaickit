"""Label nudges: a small move, in points, applied after a label has been placed.

The renderer still picks where a label goes; a nudge only fine-tunes that spot. Lengths are
numbers in points or strings with a unit (``"10pt"``, ``"0.5em"``, ``"2mm"``, ``"0.1in"``).
Pure data: no themes, no configuration files, no rendering.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from numbers import Real
from typing import Any

from mosaickit.errors import ConfigurationError

POINTS_PER_UNIT: dict[str, float] = {
    "pt": 1.0,
    "mm": 72 / 25.4,
    "cm": 72 / 2.54,
    "in": 72.0,
}
"""Fixed units and their size in points; ``em`` depends on the font size."""

_LENGTH = re.compile(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([A-Za-z]+)\s*")


@dataclass(frozen=True, slots=True)
class Nudge:
    """Move a placed label by ``dx`` points right and ``dy`` points up."""

    dx: float = 0.0
    dy: float = 0.0

    def __post_init__(self) -> None:
        for name in ("dx", "dy"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise ConfigurationError(f"Nudge.{name} must be a number of points")
            if not math.isfinite(value):
                raise ConfigurationError(f"Nudge.{name} must be finite")
            object.__setattr__(self, name, float(value))

    @property
    def is_zero(self) -> bool:
        return self.dx == 0 and self.dy == 0


def parse_length(value: Any, *, font_size: float | None = None) -> float:
    """``value`` in points: a number is points; a string carries a unit (pt, em, mm, cm, in).

    ``em`` is ``font_size`` points, so it needs ``font_size``.
    """
    if isinstance(value, bool):
        raise ConfigurationError(
            f"A length must be a number or a string with a unit, not {value!r}"
        )
    if isinstance(value, Real):
        points = float(value)
    elif isinstance(value, str):
        points = _parse_string(value, font_size)
    else:
        raise ConfigurationError(
            f"A length must be a number of points or a string such as '10pt', '0.5em' or "
            f"'2mm', not {type(value).__name__}"
        )
    if not math.isfinite(points):
        raise ConfigurationError(f"A length must be finite, got {value!r}")
    return points


def _parse_string(value: str, font_size: float | None) -> float:
    match = _LENGTH.fullmatch(value)
    if match is None:
        units = ", ".join([*POINTS_PER_UNIT, "em"])
        raise ConfigurationError(
            f"Invalid length {value!r}: use a number followed by a unit ({units}), e.g. '10pt'"
        )
    number, unit = float(match.group(1)), match.group(2).lower()
    if unit == "em":
        if font_size is None:
            raise ConfigurationError(
                f"Length {value!r} is in em, which needs the label's font size"
            )
        if isinstance(font_size, bool) or not isinstance(font_size, Real):
            raise ConfigurationError("font_size must be a number of points")
        if not math.isfinite(font_size) or font_size < 0:
            raise ConfigurationError("font_size must be finite and non-negative")
        return number * float(font_size)
    if unit not in POINTS_PER_UNIT:
        units = ", ".join([*POINTS_PER_UNIT, "em"])
        raise ConfigurationError(f"Unknown length unit {unit!r} in {value!r}; use one of {units}")
    return number * POINTS_PER_UNIT[unit]


def nudge_from(
    *,
    top: Any = None,
    bottom: Any = None,
    left: Any = None,
    right: Any = None,
    font_size: float | None = None,
) -> Nudge:
    """The nudge that moves a label up by ``top``, down by ``bottom``, and so on.

    Opposite directions combine: ``dy = top - bottom`` and ``dx = right - left``. A direction
    left as ``None`` contributes nothing.
    """

    def points(length: Any) -> float:
        return 0.0 if length is None else parse_length(length, font_size=font_size)

    return Nudge(dx=points(right) - points(left), dy=points(top) - points(bottom))


def check_nudge(owner: str, value: Any) -> Nudge | None:
    """``value`` if it is a ``Nudge`` or ``None``; anything else is a ``ConfigurationError``."""
    if value is None or isinstance(value, Nudge):
        return value
    raise ConfigurationError(f"{owner}.nudge must be a Nudge or None, not {type(value).__name__}")
