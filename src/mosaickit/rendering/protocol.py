from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from mosaickit.errors import ConfigurationError
from mosaickit.rendering.context import _RenderContext
from mosaickit.scene import Scene


@dataclass(frozen=True, slots=True)
class SaveOptions:
    transparent: bool = False
    fragment: bool = False
    tikz_scale: float = 1.0
    precision: int = 6
    mode: str = "inline"

    def __post_init__(self) -> None:
        if not math.isfinite(self.tikz_scale) or self.tikz_scale <= 0:
            raise ConfigurationError("tikz_scale must be positive and finite")
        if (
            isinstance(self.precision, bool)
            or not isinstance(self.precision, int)
            or not 0 <= self.precision <= 15
        ):
            raise ConfigurationError("precision must be an integer in [0, 15]")
        if self.mode not in ("inline", "separate"):
            raise ConfigurationError("mode must be inline or separate")


@runtime_checkable
class Renderer(Protocol):
    name: str

    def render(self, scene: Scene, context: _RenderContext) -> Any: ...

    def save(self, result: Any, target: Path, options: SaveOptions) -> list[Path]: ...
