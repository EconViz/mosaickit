"""Error messages and small value checks shared by the readers."""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mosaickit.errors import ConfigurationError
from mosaickit.palette import DEFAULT_PALETTE

if TYPE_CHECKING:
    from mosaickit.configuration.toml.fields import Context

_HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})")


class _LocatedError(ConfigurationError):
    """A ConfigurationError whose message already names the file and table."""


def _located(message: str) -> ConfigurationError:
    return _LocatedError(message)


def _relocated(error: ConfigurationError, ctx: Context, prefix: str) -> ConfigurationError:
    if isinstance(error, _LocatedError):
        return error
    return _located(_message(ctx.source, ctx.location, f"{prefix}{error}"))


def _message(source: str, location: str, problem: str) -> str:
    return f"{source}: {location} {problem}" if location else f"{source}: {problem}"


def _hint(value: Any, choices: Iterable[str], *, prefix: str = "; ") -> str:
    if not isinstance(value, str):
        return ""
    close = difflib.get_close_matches(value, list(choices), n=1)
    return f"{prefix}did you mean {close[0]!r}?" if close else ""


def _unknown(value: str, choices: Iterable[str]) -> str:
    """A did-you-mean suggestion, or the list of valid keys when nothing is close."""
    names = sorted(choices)
    return _hint(value, names) or (f"; choose from {', '.join(names)}" if names else "")


def _is_color(value: str) -> bool:
    if value.startswith("#"):
        return _HEX.fullmatch(value) is not None
    if value in DEFAULT_PALETTE:
        return True
    from matplotlib.colors import is_color_like  # only for colour names

    return bool(value) and bool(is_color_like(value))


def _path(value: str, directory: Path | None) -> str:
    resolved = Path(value).expanduser()
    if directory is not None and not resolved.is_absolute():
        resolved = directory / resolved
    return str(resolved)
