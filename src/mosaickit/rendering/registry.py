from mosaickit.errors import RenderError
from mosaickit.rendering.protocol import Renderer


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
        if name == "matplotlib":
            from mosaickit.rendering.matplotlib import MatplotlibRenderer

            return MatplotlibRenderer()
        if name == "tikz":
            from mosaickit.rendering.tikz import TikzRenderer

            return TikzRenderer()
        raise RenderError(f"Unknown renderer: {name!r}")
