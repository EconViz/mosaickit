"""Pure style resolution shared by all renderers."""

from dataclasses import dataclass, replace

from mosaickit.errors import BindingError
from mosaickit.parameter.binding import free_parameters
from mosaickit.rendering.cache import CacheKey
from mosaickit.rendering.context import _RenderContext
from mosaickit.scene import GroupLayer, Layer, LegendLayer, RegionLabelLayer, Scene, TextLayer
from mosaickit.themes import StyleBundle
from mosaickit.themes._walk import role_chain


@dataclass(frozen=True, slots=True)
class _ResolvedLayer:
    layer: Layer
    style: StyleBundle


@dataclass(frozen=True, slots=True)
class _RenderPlan:
    layers: tuple[_ResolvedLayer, ...]


def _resolve_role(context: _RenderContext, role: str, fallback: str) -> StyleBundle:
    style = context.theme.resolve(role, fallback_category=fallback)
    for overrides in (context.config_overrides, context.canvas_overrides):
        for key in reversed(role_chain(role, fallback)):
            style = overrides.get(key, StyleBundle()).merged_over(style)
    return style


def _build_render_plan(scene: Scene, context: _RenderContext) -> _RenderPlan:
    unbound = free_parameters(scene)
    if unbound:
        names = ", ".join(sorted(parameter.name for parameter in unbound))
        raise BindingError(f"Missing values for parameters: {names}")
    flattened = []

    def walk(layers: tuple[Layer, ...], z_index: float = 0) -> None:
        for layer in layers:
            if not layer.visible:
                continue
            if isinstance(layer, GroupLayer):
                walk(layer.children, z_index + layer.z_index)
            else:
                flattened.append(replace(layer, z_index=z_index + layer.z_index))

    walk(scene.layers)
    resolved = []
    for layer in sorted(flattened, key=lambda item: item.z_index):
        style = _resolve_role(context, layer.role, layer.fallback_category)
        explicit = StyleBundle(
            stroke=getattr(layer, "stroke", None),
            fill=getattr(layer, "fill", None),
            marker=getattr(layer, "marker", None),
            text=layer.style if isinstance(layer, (TextLayer, RegionLabelLayer)) else None,
            legend=layer.style if isinstance(layer, LegendLayer) else None,
        )
        style = explicit.merged_over(style)
        cache_key = CacheKey(
            layer.id,
            context.bindings,
            layer.model,
            context.spec,
            context.tolerance,
            (context.theme, style, layer),
        )

        def resolve_layer(layer: Layer = layer, style: StyleBundle = style) -> _ResolvedLayer:
            return _ResolvedLayer(layer, style)

        resolved.append(context.cache.get_or_create(cache_key, resolve_layer))
    return _RenderPlan(tuple(resolved))
