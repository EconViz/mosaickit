"""Which function draws each layer type.

Builders draw one layer, in z-order, and return its artist. Deferred passes run
after every builder, in registration order, and receive all layers of their type
at once (for work that depends on what else was drawn, such as label placement or
legends). Lookups follow the MRO, so subclasses inherit their parent's registration.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from mosaickit.errors import RenderError


@dataclass(frozen=True, slots=True)
class PassContext:
    """What deferred passes may read about the layers drawn before them."""

    handles: Mapping[str, Any]  # layer id -> artist, for layers with a legend label


Builder = Callable[[Any, Any], Any]
DeferredPass = Callable[[Any, Sequence[Any], PassContext], None]

_BUILDERS: dict[type, Builder] = {}
_PASSES: dict[type, DeferredPass] = {}


def register_builder(layer_type: type, builder: Builder) -> None:
    """Draw ``layer_type`` with ``builder(ax, resolved) -> artist``."""
    _BUILDERS[layer_type] = builder


def register_pass(layer_type: type, run: DeferredPass) -> None:
    """Draw every ``layer_type`` layer after all builders, via ``run(ax, layers, context)``."""
    _PASSES[layer_type] = run


def _lookup(table: Mapping[type, Any], layer_type: type) -> tuple[type, Any] | None:
    for base in layer_type.__mro__:
        if base in table:
            return base, table[base]
    return None


def deferred_kind(layer_type: type) -> type | None:
    found = _lookup(_PASSES, layer_type)
    return None if found is None else found[0]


def builder_for(layer_type: type) -> Builder:
    found = _lookup(_BUILDERS, layer_type)
    if found is None:
        raise RenderError(f"Unsupported layer: {layer_type.__name__}")
    return found[1]


def passes() -> tuple[tuple[type, DeferredPass], ...]:
    return tuple(_PASSES.items())
