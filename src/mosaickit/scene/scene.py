"""Persistent ordered scene snapshots."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from mosaickit.errors import ConfigurationError
from mosaickit.scene.group import GroupLayer
from mosaickit.scene.layer import Layer


def _walk(layers: Iterable[Layer]) -> Iterable[Layer]:
    for layer in layers:
        yield layer
        if isinstance(layer, GroupLayer):
            yield from _walk(layer.children)


@dataclass(frozen=True, slots=True)
class Scene:
    layers: tuple[Layer, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "layers", tuple(self.layers))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        seen = set()
        for layer in _walk(self.layers):
            if not isinstance(layer, Layer):
                raise ConfigurationError("Scene contains a non-layer value")
            if layer.id in seen:
                raise ConfigurationError(f"Duplicate layer id: {layer.id!r}")
            seen.add(layer.id)

    @classmethod
    def empty(cls) -> Scene:
        return cls()

    @property
    def ordered_layers(self) -> tuple[Layer, ...]:
        return tuple(sorted(self.layers, key=lambda layer: layer.z_index))

    def add(self, layer: Layer) -> Scene:
        return replace(self, layers=(*self.layers, layer))

    def extend(self, layers: Iterable[Layer]) -> Scene:
        return replace(self, layers=(*self.layers, *layers))

    def remove(self, layer_id: str) -> Scene:
        if layer_id not in {layer.id for layer in _walk(self.layers)}:
            raise ConfigurationError(f"Unknown layer id: {layer_id!r}")

        def without(layers: tuple[Layer, ...]) -> tuple[Layer, ...]:
            return tuple(
                replace(layer, children=without(layer.children))
                if isinstance(layer, GroupLayer)
                else layer
                for layer in layers
                if layer.id != layer_id
            )

        return replace(self, layers=without(self.layers))

    def clear(self) -> Scene:
        return replace(self, layers=())
