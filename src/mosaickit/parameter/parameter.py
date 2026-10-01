from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from mosaickit.errors import BindingError
from mosaickit.parameter.expression import Expression

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Parameter(Expression[T]):
    name: str
    value_type: type | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise BindingError("Parameter requires a non-empty name")

    def evaluate(self, bindings: Mapping) -> T:
        if self not in bindings:
            raise BindingError(f"Missing value for parameter {self.name!r}")
        value = bindings[self]
        if self.value_type is not None and not isinstance(value, self.value_type):
            raise BindingError(f"Parameter {self.name!r} requires {self.value_type.__name__}")
        try:
            hash(value)
        except TypeError as exc:
            raise BindingError(f"Parameter {self.name!r} requires a hashable value") from exc
        return value

    def free_parameters(self) -> frozenset:
        return frozenset({self})

    def values(self, values: Sequence[T]) -> ParameterValues[T]:
        return ParameterValues(self, tuple(values))


@dataclass(frozen=True, slots=True)
class ParameterValues(Generic[T]):
    parameter: Parameter[T]
    values: tuple[T, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", tuple(self.values))
        for value in self.values:
            self.parameter.evaluate({self.parameter: value})
