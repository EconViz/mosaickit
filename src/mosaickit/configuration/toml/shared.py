"""The shared sections of ``econ-viz.toml``: reading the file, fonts, colours, base theme."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import mosaickit.configuration.toml as _toml
from mosaickit.configuration.label_overrides import FigureLabels
from mosaickit.configuration.toml._helpers import _path
from mosaickit.configuration.toml.constants import FILE_NAME, SHARED_COLORS
from mosaickit.configuration.toml.figures import _NO_FIGURES, figure_labels
from mosaickit.errors import ConfigurationError
from mosaickit.text_fonts import GENERIC_FONTS, TextFonts

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on Python 3.10 only
    import tomli as tomllib


@dataclass(frozen=True, slots=True)
class SharedSettings:
    """What the shared sections of ``econ-viz.toml`` set; ``None`` keeps a default.

    ``figures`` holds the ``[figure.<stem>.label."<id>"]`` overrides (see
    :func:`figure_labels`); it is empty when the file has none.
    """

    base: str | None = None
    font: str | None = None
    math_font: str | None = None
    fonts: TextFonts | None = None
    background: str | None = None
    axis: str | None = None
    label: str | None = None
    figures: FigureLabels = field(default_factory=lambda: _NO_FIGURES)


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
    """One package's table (empty when absent); ``name`` must be in ``PACKAGES``."""
    if name not in _toml.PACKAGES:
        raise ConfigurationError(
            f"{name!r} is not a package table; choose from {sorted(_toml.PACKAGES)}"
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
    text, math_file = font.get("text"), font.get("math")
    if text is not None and text not in GENERIC_FONTS:
        raise ConfigurationError(f"{source}: [font] text must be one of {', '.join(GENERIC_FONTS)}")
    if math_file is not None and not isinstance(math_file, str):
        raise ConfigurationError(f"{source}: [font] math must be a font file path")
    fonts = _fonts(_table(data, "fonts", source), directory, source)
    colors = _table(data, "color", source)
    for key in SHARED_COLORS:
        if key in colors and not isinstance(colors[key], str):
            raise ConfigurationError(f"{source}: [color] {key} must be a colour string")
    return SharedSettings(
        base=base,
        font=text,
        math_font=_path(math_file, directory) if math_file is not None else None,
        fonts=fonts,
        background=colors.get("background"),
        axis=colors.get("axis"),
        label=colors.get("label"),
        figures=figure_labels(data, source=source),
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
    try:
        return TextFonts(**slots)  # type: ignore[arg-type]  # keys checked above
    except ConfigurationError as error:
        problem = str(error).removeprefix("TextFonts.")
        raise ConfigurationError(f"{source}: [fonts] {problem}") from None
