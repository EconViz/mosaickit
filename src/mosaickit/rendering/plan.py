"""Pure style resolution shared by all renderers."""

from dataclasses import dataclass, fields, replace

from mosaickit.errors import BindingError, ConfigurationError
from mosaickit.palette import Palette
from mosaickit.parameter.binding import free_parameters
from mosaickit.rendering.cache import CacheKey
from mosaickit.rendering.context import _RenderContext
from mosaickit.scene import GroupLayer, Layer, Scene
from mosaickit.themes import StyleBundle, resolve


@dataclass(frozen=True, slots=True)
class _ResolvedLayer:
    layer: Layer
    style: StyleBundle


@dataclass(frozen=True, slots=True)
class _RenderPlan:
    layers: tuple[_ResolvedLayer, ...]


_COLOR_FIELDS = ("color", "edge_color")


def _bind_palette(style: StyleBundle, palette: Palette, role: str) -> StyleBundle:
    """Replace palette names in every color field with the palette's colors."""
    updates = {}
    for slot in fields(style):
        value = getattr(style, slot.name)
        named = {
            name: color
            for name in _COLOR_FIELDS
            if isinstance(color := getattr(value, name, None), str)
        }
        for name, color in named.items():
            if color not in palette:
                raise ConfigurationError(
                    f"Role {role!r} {slot.name}.{name}: palette {palette.name!r} "
                    f"has no color {color!r}"
                )
        if named:
            updates[slot.name] = replace(
                value, **{name: palette[color] for name, color in named.items()}
            )
    return replace(style, **updates) if updates else style


def _resolve_role(context: _RenderContext, role: str, fallback: str) -> StyleBundle:
    """Resolve a role's style with every color name bound to the context palette."""
    style = resolve(
        context.theme,
        role,
        fallback_category=fallback,
        overrides=(context.config_overrides, context.canvas_overrides),
    )
    return _bind_palette(style, context.palette, role)


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
            **{slot: getattr(layer, name) for slot, name in layer.style_slots.items()}
        )
        style = _bind_palette(explicit.merged_over(style), context.palette, layer.role)
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
