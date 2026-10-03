from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

from mosaickit.scene.layer import Layer, _point
from mosaickit.styles import ArrowPlacement, Stroke


@dataclass(frozen=True, slots=True)
class ArrowLayer(Layer):
    role: str = field(default="annotation", kw_only=True)
    start: Any
    end: Any
    stroke: Stroke | None = None
    label: str | None = None
    arrow_placement: ArrowPlacement = ArrowPlacement.END
    fallback_category: ClassVar[str] = "annotation"
    style_slots: ClassVar[Mapping[str, str]] = {"stroke": "stroke"}

    def __post_init__(self) -> None:
        Layer.__post_init__(self)
        object.__setattr__(self, "start", _point(self.start))
        object.__setattr__(self, "end", _point(self.end))
        object.__setattr__(self, "arrow_placement", ArrowPlacement(self.arrow_placement))
