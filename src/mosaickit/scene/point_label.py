from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

from mosaickit.errors import ConfigurationError
from mosaickit.scene.layer import Layer, _point
from mosaickit.styles import TextStyle


@dataclass(frozen=True, slots=True)
class PointLabelLayer(Layer):
    """Name a point with text placed right beside it, covering nothing.

    The renderer picks the nearest position around ``point`` where the text stays
    inside the axes and touches no line, marker, filled region, or other text.
    """

    role: str = field(default="text", kw_only=True)
    point: Any
    text: str
    style: TextStyle | None = None
    fallback_category: ClassVar[str] = "text"
    style_slots: ClassVar[Mapping[str, str]] = {"text": "style"}

    def __post_init__(self) -> None:
        Layer.__post_init__(self)
        object.__setattr__(self, "point", _point(self.point))
        if not isinstance(self.text, str) or not self.text:
            raise ConfigurationError("PointLabelLayer.text must be a non-empty string")
