"""Fluent scene construction with isolated render snapshots."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from mosaickit import label_overrides
from mosaickit.canvas_spec import CanvasSpec
from mosaickit.config import Config, current_config
from mosaickit.errors import RenderError
from mosaickit.parameter import Parameter, bind
from mosaickit.rendering import RenderCache, Renderer, RendererRegistry, SaveOptions
from mosaickit.rendering.context import _RenderContext
from mosaickit.scene import Layer, Scene
from mosaickit.scene.label_nudges import with_label_nudges
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
            palette=self.config.palette,
            math_font=self.config.math_font,
            text_fonts=self.config.fonts,
        )

    def _renderer(self, renderer: Renderer | str | None = None) -> Renderer:
        selected = self.renderer if renderer is None else renderer
        return RendererRegistry().get(selected) if isinstance(selected, str) else selected

    def render(
        self, *, renderer: Renderer | str | None = None, cache: RenderCache | None = None
    ) -> Any:
        return self._renderer(renderer).render(self.snapshot(), self._context(cache))

    def _for_file(self, target: Path) -> Canvas:
        """This canvas with the active ``[figure.<stem>.label]`` overrides for ``target``.

        Those replace the nudge of the label layers they name. This canvas itself when
        nothing is active for the file's stem, so the output is then unchanged.
        """
        nudges = label_overrides.active_for(target.stem)
        scene = with_label_nudges(self._scene, nudges) if nudges else self._scene
        if scene is self._scene:
            return self
        canvas = self.copy()
        canvas._scene = scene
        return canvas

    def save(
        self,
        target: str | Path,
        *,
        renderer: Renderer | str | None = None,
        cache: RenderCache | None = None,
        **options: Any,
    ) -> list[Path]:
        """Write the canvas to ``target`` (``.png``, ``.pdf``, ``.svg`` or ``.tex``).

        The label overrides active for the file's stem (``[figure.<stem>.label."<id>"]`` in
        ``econ-viz.toml``, see :mod:`mosaickit.econ_toml`) replace the nudges of the labels
        they name before drawing. ``render()`` never applies them.
        """
        target = Path(target)
        canvas = self._for_file(target)
        if target.suffix.lower() == ".tex":
            from mosaickit.rendering.tikz import canvas_to_tikz

            standalone = bool(options.pop("standalone", options.pop("tikz_standalone", True)))
            if options:
                names = ", ".join(sorted(options))
                raise TypeError(f"unsupported TikZ export options: {names}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(canvas_to_tikz(canvas, standalone=standalone), encoding="utf-8")
            return [target]
        if target.suffix.lower() not in {".png", ".pdf", ".svg"}:
            raise RenderError(f"Unsupported output format: {target.suffix!r}")
        selected = canvas._renderer(renderer)
        result = selected.render(canvas.snapshot(), canvas._context(cache))
        try:
            return selected.save(result, target, SaveOptions(**options))
        finally:
            if hasattr(result, "close"):
                result.close()
