from __future__ import annotations

import math
import re
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, TypeVar

from mosaickit.colors import Color
from mosaickit.errors import ConfigurationError
from mosaickit.styles.base import SparseStyle, _check_size, _coerce_color, check_opacity

_DEPRECATION_MESSAGE = (
    "TextStyle.family and TextStyle.weight are deprecated; use GlyphKit for font selection. "
    "These compatibility fields may be removed in the next release."
)
T = TypeVar("T", bound="TextStyle")


@contextmanager
def _legacy_font_values() -> Iterator[None]:
    """Keep existing font values during internal construction and copying."""
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message=f"^{re.escape(_DEPRECATION_MESSAGE)}$", category=DeprecationWarning
        )
        yield


@dataclass(frozen=True, slots=True)
class TextStyle(SparseStyle):
    color: Color | str | None = None
    size: float | None = None
    family: str | None = None
    weight: str | None = None
    opacity: float | None = None
    rotation: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "color", _coerce_color(self.color))
        _check_size("TextStyle.size", self.size)
        check_opacity("TextStyle", self.opacity)
        if self.rotation is not None and not math.isfinite(self.rotation):
            raise ConfigurationError("TextStyle.rotation must be finite")
        if self.family is not None or self.weight is not None:
            warnings.warn(
                _DEPRECATION_MESSAGE,
                DeprecationWarning,
                stacklevel=3,  # Skip __post_init__ and the generated dataclass __init__.
            )

    def _replace(self: T, **changes: Any) -> T:
        with _legacy_font_values():
            return SparseStyle._replace(self, **changes)
