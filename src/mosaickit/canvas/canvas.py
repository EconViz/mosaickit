"""Fluent scene construction with isolated render snapshots."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from mosaickit.canvas_spec import CanvasSpec
from mosaickit.config import Config, current_config
from mosaickit.errors import RenderError
from mosaickit.parameter import Parameter, bind
from mosaickit.rendering import RenderCache, Renderer, RendererRegistry, SaveOptions
from mosaickit.rendering.context import _RenderContext
from mosaickit.scene import Layer, Scene
from mosaickit.themes import StyleBundle, Theme


class Canvas:
    def __init__(
        self,
        spec: CanvasSpec | None = None,
        theme: Theme | None = None,
        config: Config | None = None,
        renderer: Renderer | str | None = None,
        *,
        role_overrides: Mapping[str, StyleBundle] | None = None,
    ) -> None:
        self.config = config if config is not None else current_config()
        self.spec = spec if spec is not None else self.config.canvas_spec
        self.theme = theme if theme is not None else self.config.theme
        self.renderer = renderer if renderer is not None else self.config.renderer
        self.role_overrides = MappingProxyType(dict(role_overrides or {}))
        self._scene = Scene.empty()
        self._bindings: tuple = ()

    def add(self, layer: Layer) -> Canvas:
        self._scene = self._scene.add(layer)
        return self

    def extend(self, layers: Iterable[Layer]) -> Canvas:
        self._scene = self._scene.extend(layers)
        return self

    def remove(self, layer_id: str) -> Canvas:
        self._scene = self._scene.remove(layer_id)
        return self

    def clear(self) -> Canvas:
        self._scene = self._scene.clear()
        return self

    def snapshot(self) -> Scene:
        return self._scene

    def copy(self) -> Canvas:
        canvas = Canvas(
            self.spec, self.theme, self.config, self.renderer, role_overrides=self.role_overrides
        )
        canvas._scene = self._scene
        canvas._bindings = self._bindings
        return canvas

    def bind(self, parameter: Parameter | Mapping[Parameter, Any], value: Any = None) -> Canvas:
        bindings = dict(parameter) if isinstance(parameter, Mapping) else {parameter: value}
        for item, bound in bindings.items():
            item.evaluate({item: bound})
        canvas = self.copy()
        canvas._scene = bind(self._scene, bindings)
        canvas._bindings = (*self._bindings, *bindings.items())
        return canvas

    def _context(self, cache: RenderCache | None = None) -> _RenderContext:
        return _RenderContext(
            self.spec,
            self.theme,
            self.config.role_overrides,
            self.role_overrides,
            cache if cache is not None else RenderCache(),
            self._bindings,
        )

    def _renderer(self, renderer: Renderer | str | None = None) -> Renderer:
        selected = self.renderer if renderer is None else renderer
        return RendererRegistry().get(selected) if isinstance(selected, str) else selected

    def render(
        self, *, renderer: Renderer | str | None = None, cache: RenderCache | None = None
    ) -> Any:
        return self._renderer(renderer).render(self.snapshot(), self._context(cache))

    def save(
        self,
        target: str | Path,
        *,
        renderer: Renderer | str | None = None,
        cache: RenderCache | None = None,
        **options: Any,
    ) -> list[Path]:
        target = Path(target)
        if target.suffix.lower() not in {".png", ".pdf", ".svg", ".tex", ".pgf"}:
            raise RenderError(f"Unsupported output format: {target.suffix!r}")
        selected = self._renderer(
            renderer
            if renderer is not None
            else "tikz"
            if target.suffix.lower() in {".tex", ".pgf"}
            else None
        )
        result = selected.render(self.snapshot(), self._context(cache))
        try:
            return selected.save(result, target, SaveOptions(**options))
        finally:
            if hasattr(result, "close"):
                result.close()
