from dataclasses import dataclass, field
from typing import ClassVar

from mosaickit.scene.layer import Layer
from mosaickit.styles import LegendStyle


@dataclass(frozen=True, slots=True)
class LegendLayer(Layer):
    entries: tuple[str, ...] = ()
    style: LegendStyle | None = None
    role: str = field(default="legend", kw_only=True)
    fallback_category: ClassVar[str] = "legend"

    def __post_init__(self) -> None:
        Layer.__post_init__(self)
        object.__setattr__(self, "entries", tuple(self.entries))
