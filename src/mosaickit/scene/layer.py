"""Common immutable layer identity and geometry validation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from numbers import Real
from typing import Any, ClassVar
from uuid import uuid4

from mosaickit.errors import ConfigurationError
from mosaickit.parameter import Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class Layer:
    id: str = field(default_factory=lambda: uuid4().hex)
    role: str = "primary"
    z_index: float = 0
    visible: bool = True
    legend: str | None = None
    model: Any = field(default=None, compare=False, hash=False, repr=False)
    fallback_category: ClassVar[str] = "primary"

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ConfigurationError("Layer.id must be a non-empty string")
        if not isinstance(self.role, str) or not all(self.role.split(".")):
            raise ConfigurationError(f"Invalid layer role: {self.role!r}")
        if not math.isfinite(self.z_index):
            raise ConfigurationError("Layer.z_index must be finite")


def _point(value: Any) -> Any:
    if isinstance(value, Expression):
        return value
    try:
        values = tuple(value)
    except TypeError as exc:
        raise ConfigurationError("Expected a two-dimensional point") from exc
    if len(values) != 2:
        raise ConfigurationError("Expected a two-dimensional point")
    if any(isinstance(component, Expression) for component in values):
        return values
    if not all(isinstance(component, Real) for component in values):
        raise ConfigurationError("Point coordinates must be real numbers")
    point = (float(values[0]), float(values[1]))
    if not all(math.isfinite(component) for component in point):
        raise ConfigurationError("Point coordinates must be finite")
    return point


def _geometry(value: Any, *, minimum: int = 2) -> Any:
    if isinstance(value, Expression):
        return value
    if isinstance(value, (tuple, list)):
        points = tuple(_point(point) for point in value)
        if len(points) < minimum:
            raise ConfigurationError(f"Geometry requires at least {minimum} points")
        return points
    raise ConfigurationError("Expected an ordered point sequence")
