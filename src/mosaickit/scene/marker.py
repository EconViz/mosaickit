from dataclasses import dataclass, field
from typing import Any, ClassVar

from mosaickit.scene.layer import Layer, _geometry
from mosaickit.styles import Marker


@dataclass(frozen=True, slots=True)
class MarkerLayer(Layer):
    role: str = field(default="point", kw_only=True)
    points: Any
    marker: Marker | None = None
    fallback_category: ClassVar[str] = "point"

    def __post_init__(self) -> None:
        Layer.__post_init__(self)
        object.__setattr__(self, "points", _geometry(self.points, minimum=1))
