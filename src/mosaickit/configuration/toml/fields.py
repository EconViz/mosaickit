"""The value types of a package table: :class:`Context`, :class:`Field` and the builders."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mosaickit.configuration.toml._helpers import (
    _hint,
    _is_color,
    _located,
    _message,
    _path,
    _relocated,
)
from mosaickit.errors import ConfigurationError
from mosaickit.styles.nudge import POINTS_PER_UNIT, parse_length


@dataclass(frozen=True)
class Context:
    """Where a value comes from; passed to ``convert`` functions."""

    source: str
    base_dir: Path | None
    location: str

    def resolve(self, value: str) -> str:
        """``value`` as an absolute path, relative to the file's directory."""
        return _path(value, self.base_dir if self.base_dir is not None else Path.cwd())

    def error(self, message: str) -> ConfigurationError:
        """A ``ConfigurationError`` that names the file and the table."""
        return _located(_message(self.source, self.location, message))


@dataclass(frozen=True)
class Field:
    """One key of a package table and the attribute it sets; made by :func:`color` etc."""

    attr: str
    kind: str
    convert: Callable[[Any, Context, str], Any] = field(repr=False)


@dataclass(frozen=True)
class Pattern:
    """Tables ``[<package>.<prefix>.<name>]`` for any ``<name>``; made by :func:`pattern`."""

    prefix: str
    convert: Callable[[str, Mapping[str, Any], Context], Mapping[str, Any]] = field(repr=False)


def color(attr: str) -> Field:
    """A colour: ``#rgb``, ``#rrggbb``, ``#rrggbbaa`` or a palette or Matplotlib name."""

    def convert(value: Any, ctx: Context, key: str) -> Any:
        if not isinstance(value, str) or not _is_color(value):
            raise ctx.error(f"{key} must be a colour (#rrggbb or a colour name), got {value!r}")
        return value

    return Field(attr, "color", convert)


def number(
    attr: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    exclusive_minimum: bool = False,
) -> Field:
    """A finite int or float (not a bool), optionally bounded."""
    if exclusive_minimum and minimum == 0 and maximum is None:
        wanted = "a positive number"
    else:
        bounds = []
        if minimum is not None:
            bounds.append(f"{'>' if exclusive_minimum else '>='} {minimum:g}")
        if maximum is not None:
            bounds.append(f"<= {maximum:g}")
        wanted = "a number" + (f" {' and '.join(bounds)}" if bounds else "")

    def convert(value: Any, ctx: Context, key: str) -> Any:
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        ok = ok and math.isfinite(value)
        if ok and minimum is not None:
            ok = value > minimum if exclusive_minimum else value >= minimum
        if ok and maximum is not None:
            ok = value <= maximum
        if not ok:
            raise ctx.error(f"{key} must be {wanted}, got {value!r}")
        return value

    return Field(attr, "number", convert)


def positive(attr: str) -> Field:
    """A number greater than zero."""
    return number(attr, minimum=0, exclusive_minimum=True)


def length(attr: str) -> Field:
    """A length set in points: a number (pt) or ``"10pt"``, ``"2mm"``, ``"0.5cm"``, ``"0.1in"``.

    ``em`` is not accepted: there is no font size to measure it against. The units and their
    conversion are those of :func:`mosaickit.styles.nudge.parse_length`.
    """
    units = ", ".join(POINTS_PER_UNIT)

    def convert(value: Any, ctx: Context, key: str) -> Any:
        if isinstance(value, str) and value.strip().lower().endswith("em"):
            raise ctx.error(f"{key} cannot be in em here (no font size); use {units}")
        if isinstance(value, (int, float, str)) and not isinstance(value, bool):
            try:
                return parse_length(value)
            except ConfigurationError:
                pass
        raise ctx.error(
            f"{key} must be a length (a number of points or a string in {units}), got {value!r}"
        )

    return Field(attr, "length", convert)


def boolean(attr: str) -> Field:
    """``true`` or ``false``."""

    def convert(value: Any, ctx: Context, key: str) -> Any:
        if not isinstance(value, bool):
            raise ctx.error(f"{key} must be true or false, got {value!r}")
        return value

    return Field(attr, "boolean", convert)


def string(attr: str) -> Field:
    """Any string."""

    def convert(value: Any, ctx: Context, key: str) -> Any:
        if not isinstance(value, str):
            raise ctx.error(f"{key} must be a string, got {value!r}")
        return value

    return Field(attr, "string", convert)


def choice(attr: str, options: Iterable[str]) -> Field:
    """One of ``options``."""
    allowed = tuple(options)
    if not allowed or not all(isinstance(option, str) for option in allowed):
        raise ConfigurationError("choice() needs one or more string options")
    listed = ", ".join(repr(option) for option in allowed)

    def convert(value: Any, ctx: Context, key: str) -> Any:
        if value not in allowed:
            raise ctx.error(f"{key} must be one of {listed}, got {value!r}{_hint(value, allowed)}")
        return value

    return Field(attr, "choice", convert)


def path(attr: str) -> Field:
    """A file path, resolved against the file's directory and set as an absolute ``str``."""

    def convert(value: Any, ctx: Context, key: str) -> Any:
        if not isinstance(value, str) or not value:
            raise ctx.error(f"{key} must be a file path, got {value!r}")
        return ctx.resolve(value)

    return Field(attr, "path", convert)


def transform(attr: str, convert: Callable[[Any, Context], Any]) -> Field:
    """Any value, turned by ``convert(value, ctx)`` into the value to set.

    A ``ConfigurationError`` raised by ``convert`` is reported as
    ``"{source}: {location} {key} {message}"``; one made by ``ctx.error`` is kept as is.
    """

    def run(value: Any, ctx: Context, key: str) -> Any:
        try:
            return convert(value, ctx)
        except ConfigurationError as error:
            raise _relocated(error, ctx, f"{key} ") from None

    return Field(attr, "transform", run)


def pattern(
    prefix: str, convert: Callable[[str, Mapping[str, Any], Context], Mapping[str, Any]]
) -> Pattern:
    """Tables ``[<package>.<prefix>.<name>]``: ``convert(name, table, ctx)`` -> attr updates."""
    if not prefix or any(not part for part in prefix.split(".")):
        raise ConfigurationError(f"pattern prefix must be a dotted name, got {prefix!r}")
    return Pattern(prefix, convert)
