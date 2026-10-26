"""Helpers of :class:`Schema`: merging tables, setting attributes, writing the template."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import is_dataclass, replace
from typing import Any

from mosaickit.errors import ConfigurationError


def _merge(low: Mapping[str, Any], high: Mapping[str, Any]) -> dict[str, Any]:
    """``low`` updated by ``high``, table by table."""
    merged = dict(low)
    for key, value in high.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class _Node:
    __slots__ = ("children", "has_value", "value")

    def __init__(self) -> None:
        self.has_value = False
        self.value: Any = None
        self.children: dict[str, _Node] = {}


def _apply(target: Any, updates: Iterable[tuple[str, Any]], package: str) -> Any:
    """Set dotted attributes in order, rebuilding each frozen dataclass once."""
    root = _Node()
    for attr, value in updates:
        node = root
        for part in attr.split("."):
            node = node.children.setdefault(part, _Node())
        node.has_value, node.value = True, value
        node.children.clear()  # a later whole value replaces earlier nested ones
    return _rebuild(target, root, package, "")


def _rebuild(obj: Any, node: _Node, package: str, where: str) -> Any:
    if not node.children:
        return obj
    if not is_dataclass(obj) or isinstance(obj, type):
        raise ConfigurationError(
            f"Schema {package!r}: cannot set {', '.join(node.children)} on "
            f"{where or 'the target'}, which is not a dataclass instance"
        )
    changes = {}
    for name, child in node.children.items():
        dotted = f"{where}.{name}" if where else name
        if not hasattr(obj, name):
            raise ConfigurationError(f"Schema {package!r}: target has no attribute {dotted!r}")
        current = child.value if child.has_value else getattr(obj, name)
        changes[name] = _rebuild(current, child, package, dotted)
    try:
        return replace(obj, **changes)
    except (TypeError, ValueError) as error:
        raise ConfigurationError(
            f"Schema {package!r}: cannot set {where or 'the target'}: {error}"
        ) from error


def _dotted_get(obj: Any, attr: str) -> Any:
    for part in attr.split("."):
        obj = getattr(obj, part, None)
    return obj


def _toml_value(value: Any) -> str:
    if hasattr(value, "to_hex"):
        value = value.to_hex()
    if isinstance(value, (bool, str)) or (isinstance(value, (int, float)) and math.isfinite(value)):
        return _toml_scalar(value)
    if isinstance(value, (list, tuple)) and all(
        isinstance(item, (bool, str, int, float)) for item in value
    ):
        return "[" + ", ".join(_toml_scalar(item) for item in value) + "]"
    return "..."


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return repr(value)
