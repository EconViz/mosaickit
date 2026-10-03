from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from mosaickit.rendering.context import _RenderContext
from mosaickit.scene import Scene


@dataclass(frozen=True, slots=True)
class SaveOptions:
    """How a rendered result is written.

    ``expand`` grows the saved canvas just enough to include anything drawn past
    its edges (such as gutter text); it never crops, so a diagram that fits keeps
    exactly the size its ``CanvasSpec`` asks for.
    """

    transparent: bool = False
    expand: bool = True


@runtime_checkable
class Renderer(Protocol):
    name: str

    def render(self, scene: Scene, context: _RenderContext) -> Any: ...

    def save(self, result: Any, target: Path, options: SaveOptions) -> list[Path]: ...
