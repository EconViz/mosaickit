"""Common immutable layer identity and geometry validation."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from numbers import Real
from typing import Any, ClassVar
from uuid import uuid4

import numpy as np

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
    # StyleBundle slot -> name of the field holding this layer's explicit style for it.
    style_slots: ClassVar[Mapping[str, str]] = {}

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ConfigurationError("Layer.id must be a non-empty string")
        if not isinstance(self.role, str) or not all(self.role.split(".")):
            raise ConfigurationError(f"Invalid layer role: {self.role!r}")
        if not math.isfinite(self.z_index):
            raise ConfigurationError("Layer.z_index must be finite")


def _text(owner: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{owner} must be a non-empty string")
    return value


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


# NumPy's fixed cost outweighs the per-point loop below this many points.
_PLAIN_MINIMUM = 8


def _plain_points(value: Any, minimum: int) -> tuple[tuple[float, float], ...] | None:
    """A long list of plain numeric points, validated as one array, or None.

    Returns what :func:`_point` would build for every point: floats, all finite. Anything
    else (expressions, ragged input, too few points, non-finite values) goes through the
    per-point path, which also raises the errors.
    """
    if type(value) not in (tuple, list) or len(value) < max(minimum, _PLAIN_MINIMUM):
        return None
    try:
        array = np.asarray(value)
    except (TypeError, ValueError):
        return None
    if array.ndim != 2 or array.shape[1] != 2 or array.dtype.kind not in "fiub":
        return None
    as_float = array.astype(float)
    if not np.all(np.isfinite(as_float)):
        return None
    return tuple((x, y) for x, y in as_float.tolist())


def _geometry(value: Any, *, minimum: int = 2) -> Any:
    if isinstance(value, Expression):
        return value
    plain = _plain_points(value, minimum)
    if plain is not None:
        return plain
    if isinstance(value, (tuple, list)):
        points = tuple(_point(point) for point in value)
        if len(points) < minimum:
            raise ConfigurationError(f"Geometry requires at least {minimum} points")
        return points
    raise ConfigurationError("Expected an ordered point sequence")
