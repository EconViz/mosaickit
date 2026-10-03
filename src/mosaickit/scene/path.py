from dataclasses import dataclass
from typing import Any

from mosaickit.scene.layer import Layer, _geometry
from mosaickit.styles import ArrowPlacement, Stroke


@dataclass(frozen=True, slots=True)
class PathLayer(Layer):
    path: Any
    stroke: Stroke | None = None
    arrow_placement: ArrowPlacement = ArrowPlacement.END
    clip: bool = True

    def __post_init__(self) -> None:
        Layer.__post_init__(self)
        object.__setattr__(self, "path", _geometry(self.path))
        object.__setattr__(self, "arrow_placement", ArrowPlacement(self.arrow_placement))
        object.__setattr__(self, "clip", bool(self.clip))
