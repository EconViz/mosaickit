import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

from mosaickit.errors import ConfigurationError
from mosaickit.scene.layer import Layer, _point
from mosaickit.styles import TextStyle

TEXT_ANCHORS: dict[str, tuple[str, str]] = {
    "center": ("center", "center"),
    "left": ("left", "center"),
    "right": ("right", "center"),
    "top": ("center", "top"),
    "bottom": ("center", "bottom"),
    "top-left": ("left", "top"),
    "top-right": ("right", "top"),
    "bottom-left": ("left", "bottom"),
    "bottom-right": ("right", "bottom"),
}
"""Anchor name -> (horizontal, vertical) alignment of the text box at ``position``."""


@dataclass(frozen=True, slots=True)
class TextLayer(Layer):
    role: str = field(default="text", kw_only=True)
    position: Any
    text: Any
    style: TextStyle | None = None
    offset: tuple[float, float] = (0, 0)
    anchor: str = "center"
    math: bool = False
    fallback_category: ClassVar[str] = "text"
    style_slots: ClassVar[Mapping[str, str]] = {"text": "style"}

    def __post_init__(self) -> None:
        Layer.__post_init__(self)
        object.__setattr__(self, "position", _point(self.position))
        object.__setattr__(self, "offset", tuple(self.offset))
        if len(self.offset) != 2 or not all(math.isfinite(v) for v in self.offset):
            raise ConfigurationError("TextLayer.offset must contain two finite values")
        if self.anchor not in TEXT_ANCHORS:
            raise ConfigurationError(f"Unsupported text anchor: {self.anchor}")
