from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from mosaickit.rendering.context import _RenderContext
from mosaickit.scene import Scene


@dataclass(frozen=True, slots=True)
class SaveOptions:
    transparent: bool = False


@runtime_checkable
class Renderer(Protocol):
    name: str

    def render(self, scene: Scene, context: _RenderContext) -> Any: ...

    def save(self, result: Any, target: Path, options: SaveOptions) -> list[Path]: ...
