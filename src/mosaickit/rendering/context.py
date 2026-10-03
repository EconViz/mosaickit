from collections.abc import Mapping
from dataclasses import dataclass, field

from mosaickit.canvas_spec import CanvasSpec
from mosaickit.palette import DEFAULT_PALETTE, Palette
from mosaickit.rendering.cache import RenderCache
from mosaickit.themes import StyleBundle, Theme


@dataclass(frozen=True, slots=True)
class _RenderContext:
    spec: CanvasSpec
    theme: Theme
    config_overrides: Mapping[str, StyleBundle] = field(default_factory=dict)
    canvas_overrides: Mapping[str, StyleBundle] = field(default_factory=dict)
    cache: RenderCache = field(default_factory=RenderCache)
    bindings: tuple = ()
    tolerance: float = 1e-6
    palette: Palette = DEFAULT_PALETTE
