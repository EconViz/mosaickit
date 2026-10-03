from importlib import import_module

from mosaickit.errors import RenderError
from mosaickit.rendering.protocol import Renderer

# Built-in backends by name, loaded on first use so the core never imports a
# drawing library itself.
_BUILTINS = {"matplotlib": "mosaickit.rendering.matplotlib:MatplotlibRenderer"}


class RendererRegistry:
    def __init__(self) -> None:
        self._renderers: dict[str, Renderer] = {}

    def register(self, renderer: Renderer) -> None:
        if not isinstance(renderer, Renderer):
            raise RenderError("Renderer must implement name, render, and save")
        if renderer.name in self._renderers:
            raise RenderError(f"Renderer already registered: {renderer.name!r}")
        self._renderers[renderer.name] = renderer

    def get(self, name: str) -> Renderer:
        if name in self._renderers:
            return self._renderers[name]
        if name in _BUILTINS:
            module, attribute = _BUILTINS[name].split(":")
            renderer: Renderer = getattr(import_module(module), attribute)()
            return renderer
        raise RenderError(f"Unknown renderer: {name!r}")
