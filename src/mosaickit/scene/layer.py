"""Common immutable layer identity and geometry validation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, ClassVar
from uuid import uuid4

from bezierkit import CubicBezierSegment, PiecewiseBezier, Point
from bezierkit.core.geometry.point_set import PointSet

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
    if not isinstance(value, Point):
        try:
            values = tuple(value)
            if len(values) == 2 and any(isinstance(v, Expression) for v in values):
                return values
            value = Point(*values)
        except (TypeError, ValueError) as exc:
            raise ConfigurationError("Expected a two-dimensional point") from exc
    if value.dimension != 2:
        raise ConfigurationError("Scene points must have dimension 2")
    return value


def _geometry(value: Any, *, minimum: int = 2) -> Any:
    if isinstance(value, Expression):
        return value
    if isinstance(value, (PiecewiseBezier, CubicBezierSegment)):
        if value.dimension != 2:
            raise ConfigurationError("Scene paths must have dimension 2")
        return value
    if isinstance(value, PointSet) or isinstance(value, (tuple, list)):
        points = tuple(_point(point) for point in value)
        if len(points) < minimum:
            raise ConfigurationError(f"Geometry requires at least {minimum} points")
        return points
    raise ConfigurationError("Expected BezierKit geometry or an ordered point sequence")
