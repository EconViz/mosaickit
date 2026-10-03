from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

from mosaickit.scene.layer import Layer, _geometry
from mosaickit.styles import Fill, Stroke


@dataclass(frozen=True, slots=True)
class FillLayer(Layer):
    role: str = field(default="region", kw_only=True)
    boundary: Any
    fill: Fill | None = None
    stroke: Stroke | None = None
    fallback_category: ClassVar[str] = "region"
    style_slots: ClassVar[Mapping[str, str]] = {"fill": "fill", "stroke": "stroke"}

    def __post_init__(self) -> None:
        Layer.__post_init__(self)
        object.__setattr__(self, "boundary", _geometry(self.boundary, minimum=3))
