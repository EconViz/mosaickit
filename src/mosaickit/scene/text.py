import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

from mosaickit.errors import ConfigurationError
from mosaickit.scene.layer import Layer, _point
from mosaickit.styles import Nudge, TextStyle
from mosaickit.styles.nudge import check_nudge

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
    """Text at ``position``, moved by ``offset`` points; ``nudge`` adds a further move."""

    role: str = field(default="text", kw_only=True)
    position: Any
    text: Any
    style: TextStyle | None = None
    offset: tuple[float, float] = (0, 0)
    anchor: str = "center"
    math: bool = False
    nudge: Nudge | None = field(default=None, kw_only=True)
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
        check_nudge("TextLayer", self.nudge)

    @property
    def total_offset(self) -> tuple[float, float]:
        """``offset`` plus ``nudge``, in points; just ``offset`` when there is no nudge."""
        if self.nudge is None:
            return self.offset
        return (self.offset[0] + self.nudge.dx, self.offset[1] + self.nudge.dy)
