import math
from dataclasses import dataclass, field
from typing import Any, ClassVar

from mosaickit.errors import ConfigurationError
from mosaickit.scene.layer import Layer, _point
from mosaickit.styles import TextStyle


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

    def __post_init__(self) -> None:
        Layer.__post_init__(self)
        object.__setattr__(self, "position", _point(self.position))
        object.__setattr__(self, "offset", tuple(self.offset))
        if len(self.offset) != 2 or not all(math.isfinite(v) for v in self.offset):
            raise ConfigurationError("TextLayer.offset must contain two finite values")
        if self.anchor not in ("center", "left", "right", "top", "bottom"):
            raise ConfigurationError(f"Unsupported text anchor: {self.anchor}")
