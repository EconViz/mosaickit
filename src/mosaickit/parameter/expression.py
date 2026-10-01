"""Immutable expression trees; equality is structural, comparisons are explicit."""

from __future__ import annotations

import operator
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from mosaickit.errors import BindingError

T = TypeVar("T")
OPERATORS = {
    "add": operator.add,
    "sub": operator.sub,
    "mul": operator.mul,
    "truediv": operator.truediv,
    "pow": operator.pow,
    "lt": operator.lt,
    "le": operator.le,
    "gt": operator.gt,
    "ge": operator.ge,
    "eq": operator.eq,
    "ne": operator.ne,
}


class Expression(Generic[T], ABC):
    @abstractmethod
    def evaluate(self, bindings: Mapping) -> T: ...

    @abstractmethod
    def free_parameters(self) -> frozenset: ...

    def _op(self, name: str, other: Any) -> Expression:
        return _BinOp(name, self, _wrap(other))

    def __add__(self, other: Any) -> Expression:
        return self._op("add", other)

    def __radd__(self, other: Any) -> Expression:
        return _wrap(other)._op("add", self)

    def __sub__(self, other: Any) -> Expression:
        return self._op("sub", other)

    def __rsub__(self, other: Any) -> Expression:
        return _wrap(other)._op("sub", self)

    def __mul__(self, other: Any) -> Expression:
        return self._op("mul", other)

    def __rmul__(self, other: Any) -> Expression:
        return _wrap(other)._op("mul", self)

    def __truediv__(self, other: Any) -> Expression:
        return self._op("truediv", other)

    def __rtruediv__(self, other: Any) -> Expression:
        return _wrap(other)._op("truediv", self)

    def __pow__(self, other: Any) -> Expression:
        return self._op("pow", other)

    def __neg__(self) -> Expression:
        return self * -1

    def __lt__(self, other: Any) -> Expression:
        return self._op("lt", other)

    def __le__(self, other: Any) -> Expression:
        return self._op("le", other)

    def __gt__(self, other: Any) -> Expression:
        return self._op("gt", other)

    def __ge__(self, other: Any) -> Expression:
        return self._op("ge", other)

    def equals(self, other: Any) -> Expression[bool]:
        return self._op("eq", other)

    def __bool__(self) -> bool:
        raise BindingError("Evaluate expressions before using them as booleans")


@dataclass(frozen=True, slots=True)
class Constant(Expression[T]):
    value: T

    def __post_init__(self) -> None:
        try:
            hash(self.value)
        except TypeError as exc:
            raise BindingError("Constant values must be immutable and hashable") from exc

    def evaluate(self, bindings: Mapping) -> T:
        return self.value

    def free_parameters(self) -> frozenset:
        return frozenset()


def _wrap(value: Any) -> Expression:
    return value if isinstance(value, Expression) else Constant(value)


@dataclass(frozen=True, slots=True)
class _BinOp(Expression):
    operation: str
    left: Expression
    right: Expression

    def evaluate(self, bindings: Mapping) -> Any:
        try:
            return OPERATORS[self.operation](
                self.left.evaluate(bindings), self.right.evaluate(bindings)
            )
        except (TypeError, ValueError, ArithmeticError) as exc:
            names = ", ".join(sorted(p.name for p in self.free_parameters()))
            raise BindingError(f"Cannot evaluate expression for parameters {names}: {exc}") from exc

    def free_parameters(self) -> frozenset:
        return self.left.free_parameters() | self.right.free_parameters()
