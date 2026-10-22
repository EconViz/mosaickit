from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from typing import Any

from mosaickit.parameter.expression import Constant, Expression, _BinOp, _wrap
from mosaickit.parameter.parameter import Parameter
from mosaickit.styles.base import SparseStyle

_NONE: frozenset[Parameter] = frozenset()


def _plain_points(value: Any) -> bool:
    """Whether ``value`` is a sequence of ``(float, float)`` tuples, which hold no parameters."""
    return all(
        type(item) is tuple and len(item) == 2 and type(item[0]) is float and type(item[1]) is float
        for item in value
    )


def free_parameters(value: Any) -> frozenset[Parameter]:
    """Find unbound parameters before creating backend state."""
    kind = type(value)
    if kind is float or kind is int or kind is str or kind is bool or value is None:
        return _NONE
    if isinstance(value, Expression):
        return value.free_parameters()
    if (kind is tuple or kind is list) and value and _plain_points(value):
        return _NONE
    if isinstance(value, (tuple, list)):
        return frozenset().union(*(free_parameters(item) for item in value))
    if is_dataclass(value) and type(value).__module__.startswith("mosaickit."):
        return frozenset().union(
            *(
                free_parameters(getattr(value, field.name))
                for field in fields(value)
                if field.name != "model"
            )
        )
    return frozenset()


def bind(value: Any, bindings: Mapping[Parameter, Any]) -> Any:
    """Partially bind expressions throughout immutable model dataclasses."""
    if isinstance(value, Expression):
        if value.free_parameters().issubset(bindings):
            return value.evaluate(bindings)
        if isinstance(value, _BinOp):
            return _BinOp(
                value.operation,
                _wrap(bind(value.left, bindings)),
                _wrap(bind(value.right, bindings)),
            )
        return value
    if isinstance(value, tuple):
        return tuple(bind(item, bindings) for item in value)
    if isinstance(value, Mapping):
        return {key: bind(item, bindings) for key, item in value.items()}
    if (
        is_dataclass(value)
        and not isinstance(value, (type, Constant))
        and type(value).__module__.startswith("mosaickit.")
    ):
        changes = {
            f.name: bind(getattr(value, f.name), bindings)
            for f in fields(value)
            if f.init and f.name != "model"
        }
        if isinstance(value, SparseStyle):
            return value._replace(**changes)
        return replace(value, **changes)
    return value
