"""The plain-input fast paths return what the general paths return."""

from __future__ import annotations

import numpy as np
import pytest

from mosaickit.errors import ConfigurationError
from mosaickit.parameter import Parameter
from mosaickit.parameter.binding import free_parameters
from mosaickit.scene import layer


def general_geometry(value, minimum=2):
    """_geometry without the array fast path."""
    if isinstance(value, layer.Expression):
        return value
    if isinstance(value, (tuple, list)):
        points = tuple(layer._point(point) for point in value)
        if len(points) < minimum:
            raise ConfigurationError(f"Geometry requires at least {minimum} points")
        return points
    raise ConfigurationError("Expected an ordered point sequence")


GOOD = {
    "floats": [(0.5 * i, 1.0 + i) for i in range(12)],
    "ints": [(i, 2 * i) for i in range(12)],
    "mixed": [(i, 0.25 * i) for i in range(12)],
    "bools": [(True, False)] * 9,
    "numpy-scalars": [(np.float64(i), np.float32(i)) for i in range(12)],
    "arrays": [np.array([i, i + 1.5]) for i in range(12)],
    "tuple": tuple((float(i), float(i * i)) for i in range(12)),
    "short": [(0.0, 1.0), (2.0, 3.0)],
}


@pytest.mark.parametrize("name", GOOD)
def test_geometry_matches_the_per_point_path(name: str) -> None:
    value = GOOD[name]
    assert layer._geometry(value) == general_geometry(value)
    assert all(type(c) is float for point in layer._geometry(value) for c in point)


def test_geometry_with_large_integers_rounds_as_float_does() -> None:
    value = [(2**60 + i, 1) for i in range(12)]
    assert layer._geometry(value) == general_geometry(value)


@pytest.mark.parametrize(
    "value",
    [
        [(0.0, float("nan"))] * 10,
        [(0.0, float("inf"))] * 10,
        [(0.0, 1.0, 2.0)] * 10,
        [(0.0, "a")] * 10,
        [(0.0, 1.0)] * 9 + [(1.0,)],
        "not points",
        7,
    ],
)
def test_geometry_raises_what_the_per_point_path_raises(value) -> None:
    with pytest.raises(ConfigurationError) as general:
        general_geometry(value)
    with pytest.raises(ConfigurationError) as fast:
        layer._geometry(value)
    assert str(fast.value) == str(general.value)


def test_geometry_minimum_is_enforced() -> None:
    with pytest.raises(ConfigurationError):
        layer._geometry([(0.0, 0.0)] * 3, minimum=4)


def test_geometry_keeps_expressions() -> None:
    p = Parameter("p")
    value = [(0.0, 1.0)] * 9 + [(p, 2.0)]
    assert layer._geometry(value) == general_geometry(value)


def test_free_parameters_of_plain_values() -> None:
    p = Parameter("p")
    for value in (1.0, 2, "text", True, None, ((0.0, 1.0),) * 12, [(1.0, 2.0)] * 12, ()):
        assert free_parameters(value) == frozenset()
    assert free_parameters(((0.0, 1.0), (p, 2.0))) == frozenset({p})
    assert free_parameters([p, 1.0]) == frozenset({p})
