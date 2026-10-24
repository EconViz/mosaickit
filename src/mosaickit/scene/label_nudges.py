"""Replace the nudges of chosen labels in a scene, by layer id."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, replace
from typing import Any

from mosaickit.scene.brace_parts import BraceParts
from mosaickit.scene.group import GroupLayer
from mosaickit.scene.layer import Layer
from mosaickit.scene.scene import Scene
from mosaickit.styles.nudge import Nudge


def with_label_nudges(scene: Scene, nudges: Mapping[str, Nudge]) -> Scene:
    """``scene`` with the nudge of every label layer whose id is in ``nudges`` replaced.

    A layer matches by its id. A brace also matches ``<id>.label``, the id its label has in
    the drawing, unless another layer has that id. Layers without a ``nudge`` and ids that
    match nothing are left alone. The scene itself is returned when nothing changes.
    """
    if not nudges:
        return scene
    layers = _replace_in(scene.layers, nudges, _all_ids(scene.layers))
    return scene if layers is scene.layers else replace(scene, layers=layers)


def _all_ids(layers: tuple[Layer, ...]) -> frozenset[str]:
    ids: set[str] = set()
    for layer in layers:
        ids.add(layer.id)
        if isinstance(layer, GroupLayer):
            ids |= _all_ids(layer.children)
    return frozenset(ids)


def _replace_in(
    layers: tuple[Layer, ...], nudges: Mapping[str, Nudge], taken: frozenset[str]
) -> tuple[Layer, ...]:
    changed = False
    result = []
    for layer in layers:
        new = _replace_layer(layer, nudges, taken)
        changed = changed or new is not layer
        result.append(new)
    return tuple(result) if changed else layers


def _replace_layer(layer: Layer, nudges: Mapping[str, Nudge], taken: frozenset[str]) -> Layer:
    if isinstance(layer, GroupLayer):
        children = _replace_in(layer.children, nudges, taken)
        return layer if children is layer.children else replace(layer, children=children)
    if "nudge" not in {item.name for item in fields(layer)}:  # type: ignore[arg-type]
        return layer
    nudge = nudges.get(layer.id)
    if nudge is None and isinstance(layer, BraceParts):
        label_id = f"{layer.id}.label"
        nudge = nudges.get(label_id) if label_id not in taken else None
    if nudge is None or nudge == getattr(layer, "nudge", None):
        return layer
    changed: Any = layer
    return replace(changed, nudge=nudge)  # type: ignore[no-any-return]
