"""Label helpers: when a title is math, subscripts and primes."""

from __future__ import annotations


def is_symbol(label: str) -> bool:
    """Single letters and ``$...$`` titles are set as math; words stay upright."""
    wrapped = len(label) > 1 and label.startswith("$") and label.endswith("$")
    return wrapped or (len(label) == 1 and label.isalpha())


def indexed(label: str, index: int) -> str:
    """``label`` with a subscript: ``$Y$`` -> ``$Y_1$``, ``Y`` -> ``Y_1``."""
    if label.startswith("$") and label.endswith("$"):
        return f"{label[:-1]}_{index}$"
    return f"{label}_{index}"


def primed(label: str, primes: int = 1) -> str:
    """``label`` with ``primes`` primes after its last symbol: ``$A$`` -> ``$A'$``."""
    if not primes:
        return label
    mark = "'" * primes
    return f"{label[:-1]}{mark}$" if label.startswith("$") and label.endswith("$") else label + mark
