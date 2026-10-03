"""Layers attached to an axis rather than to a point in the plot."""

import math
from dataclasses import dataclass
from numbers import Real
from typing import Any

from mosaickit.errors import ConfigurationError
from mosaickit.parameter import Expression
from mosaickit.scene.layer import Layer

AXES = ("x", "y")


def _axis_value(owner: str, value: Any) -> Any:
    if isinstance(value, Expression):
        return value
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ConfigurationError(f"{owner} requires a finite number")
    return float(value)


@dataclass(frozen=True, slots=True)
class AxisLayer(Layer):
    """Base for layers positioned by a value on the ``"x"`` or ``"y"`` axis.

    The y axis is the plot's left edge and the x axis its bottom edge; what lies
    outside them is the gutter.
    """

    axis: str

    def __post_init__(self) -> None:
        Layer.__post_init__(self)
        if self.axis not in AXES:
            raise ConfigurationError(f"Unsupported axis: {self.axis!r} (use 'x' or 'y')")
