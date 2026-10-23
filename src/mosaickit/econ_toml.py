"""The settings file every EconViz diagram package reads: ``econ-viz.toml``.

One file styles every package. The shared sections set what all diagrams have in
common, and each package reads them the same way through :func:`shared_settings`::

    base = "default"          # a package's built-in theme to start from

    [font]
    text = "serif"            # generic font: sans, serif or mono
    math = "fonts/math.otf"   # math font file

    [fonts]                   # font files that replace a generic font
    serif = ["fonts/Regular.otf", "fonts/Bold.otf"]

    [color]
    background = "#ffffff"
    axis = "#1a1a1a"
    label = "#1a1a1a"         # text

utility-viz, the first package, keeps its own settings at the top level (more keys
in ``[color]``, ``[stroke.*]``, ``[marker.*]`` ...). Every other package keeps its
own settings in one table named in :data:`PACKAGE_TABLES`, for example
``[principle.color]``, and ignores the tables of the others.

Relative paths are resolved against the file's directory.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mosaickit.errors import ConfigurationError
from mosaickit.text_fonts import GENERIC_FONTS, TextFonts

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on Python 3.10 only
    import tomli as tomllib

FILE_NAME = "econ-viz.toml"
# The tables that belong to one package each; a package skips the others' tables.
PACKAGE_TABLES = frozenset({"principle", "micro", "macro", "trade", "dsge", "game"})
# The top-level keys every package understands.
SHARED_SECTIONS = frozenset({"base", "font", "fonts", "color"})
SHARED_COLORS = ("background", "axis", "label")


@dataclass(frozen=True, slots=True)
class SharedSettings:
    """What the shared sections of ``econ-viz.toml`` set; ``None`` keeps a default."""

    base: str | None = None
    font: str | None = None
    math_font: str | None = None
    fonts: TextFonts | None = None
    background: str | None = None
    axis: str | None = None
    label: str | None = None


def find(directory: str | Path | None = None) -> Path | None:
    """``econ-viz.toml`` in ``directory`` (the working directory by default), if any."""
    path = Path(directory or ".") / FILE_NAME
    return path if path.is_file() else None


def read(path: str | Path) -> dict[str, Any]:
    """Parse a settings file; raise ``ConfigurationError`` with its path on bad TOML."""
    source = Path(path)
    try:
        return tomllib.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigurationError(f"config file not found: {source}") from None
    except tomllib.TOMLDecodeError as error:
        raise ConfigurationError(f"{source}: {error}") from None


def package_table(
    data: Mapping[str, Any], name: str, *, source: str = "config"
) -> Mapping[str, Any]:
    """One package's table (empty when absent); ``name`` must be in ``PACKAGE_TABLES``."""
    if name not in PACKAGE_TABLES:
        raise ConfigurationError(
            f"{name!r} is not a package table; choose from {sorted(PACKAGE_TABLES)}"
        )
    table = data.get(name, {})
    if not isinstance(table, Mapping):
        raise ConfigurationError(f"{source}: [{name}] must be a table")
    return table


def shared_settings(
    data: Mapping[str, Any], *, base_dir: str | Path | None = None, source: str = "config"
) -> SharedSettings:
    """Read the shared sections; keys a package adds to them are left to that package."""
    directory = Path(base_dir) if base_dir is not None else None
    base = data.get("base")
    if base is not None and not isinstance(base, str):
        raise ConfigurationError(f"{source}: base must be a string")
    font = _table(data, "font", source)
    text, math = font.get("text"), font.get("math")
    if text is not None and text not in GENERIC_FONTS:
        raise ConfigurationError(f"{source}: [font] text must be one of {', '.join(GENERIC_FONTS)}")
    if math is not None and not isinstance(math, str):
        raise ConfigurationError(f"{source}: [font] math must be a font file path")
    fonts = _fonts(_table(data, "fonts", source), directory, source)
    colors = _table(data, "color", source)
    for key in SHARED_COLORS:
        if key in colors and not isinstance(colors[key], str):
            raise ConfigurationError(f"{source}: [color] {key} must be a colour string")
    return SharedSettings(
        base=base,
        font=text,
        math_font=_path(math, directory) if math is not None else None,
        fonts=fonts,
        background=colors.get("background"),
        axis=colors.get("axis"),
        label=colors.get("label"),
    )


def _table(data: Mapping[str, Any], key: str, source: str) -> Mapping[str, Any]:
    table = data.get(key, {})
    if not isinstance(table, Mapping):
        raise ConfigurationError(f"{source}: [{key}] must be a table")
    return table


def _fonts(table: Mapping[str, Any], directory: Path | None, source: str) -> TextFonts | None:
    if not table:
        return None
    unknown = set(table) - set(GENERIC_FONTS)
    if unknown:
        raise ConfigurationError(
            f"{source}: unknown [fonts] slot(s) {', '.join(sorted(unknown))}; "
            f"choose from {', '.join(GENERIC_FONTS)}"
        )
    slots: dict[str, tuple[Path, ...]] = {}
    for slot, value in table.items():
        files = [value] if isinstance(value, str) else value
        if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
            raise ConfigurationError(f"{source}: [fonts] {slot} must be a path or a list of paths")
        slots[slot] = tuple(Path(_path(item, directory)) for item in files)
    return TextFonts(**slots)  # type: ignore[arg-type]  # keys checked above


def _path(value: str, directory: Path | None) -> str:
    path = Path(value).expanduser()
    if directory is not None and not path.is_absolute():
        path = directory / path
    return str(path)


__all__ = [
    "FILE_NAME",
    "PACKAGE_TABLES",
    "SHARED_COLORS",
    "SHARED_SECTIONS",
    "SharedSettings",
    "find",
    "package_table",
    "read",
    "shared_settings",
]
