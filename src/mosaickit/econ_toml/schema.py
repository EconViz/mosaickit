"""The :class:`Schema` a package declares to read its table of ``econ-viz.toml``."""

from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import mosaickit.econ_toml as _toml
from mosaickit.econ_toml._apply import _apply, _dotted_get, _merge, _toml_value
from mosaickit.econ_toml._helpers import _hint, _is_color, _located, _message, _relocated, _unknown
from mosaickit.econ_toml.config import ConfigBase
from mosaickit.econ_toml.constants import (
    _SHARED_KEYS,
    FILE_NAME,
    LEGACY_SECTIONS,
    SHARED_COLORS,
    SHARED_NAMES,
    SHARED_SECTIONS,
)
from mosaickit.econ_toml.fields import Context, Field, Pattern
from mosaickit.econ_toml.shared import find, read, shared_settings
from mosaickit.errors import ConfigurationError


@dataclass(frozen=True)
class Schema:
    """What one package reads from ``econ-viz.toml`` and the object it builds.

    Parameters
    ----------
    package : str
        The package's table, one of :data:`PACKAGES`.
    base : mapping
        Built-in theme name -> factory of the target object; must contain ``"default"``.
    fields : mapping
        Dotted key inside ``[<package>]`` (``"language"``, ``"color.demand"``) -> :class:`Field`.
    patterns : mapping
        Prefix -> :class:`Pattern` for tables with free names such as ``[utility.stroke.ic]``.
    shared : mapping
        Shared setting (one of :data:`SHARED_NAMES`) -> attribute on the target, or a
        :class:`Field` whose ``convert`` turns the shared value first. Unmapped shared
        settings are ignored by this package.
    legacy_top_level : bool
        Also read this package's keys from the top level, with one warning per load
        (utility-viz before 2.0). Keys in ``[<package>]`` win.
    legacy_warning : callable, optional
        Called once per load with the warning message; default ``warnings.warn`` with
        ``FutureWarning``.
    finalize : callable, optional
        ``finalize(target, ctx)`` -> the final target.
    docs : mapping
        Field key or pattern prefix -> one-line comment for :meth:`template`.

    Notes
    -----
    The top-level ``[figure]`` table (per-figure label overrides, see :func:`figure_labels`)
    belongs to mosaickit, like ``[font]`` and ``[color]``: a schema neither declares nor
    receives it, but every :meth:`build` checks it and :class:`ConfigBase` keeps it.
    """

    package: str
    base: Mapping[str, Callable[[], Any]]
    fields: Mapping[str, Field] = field(default_factory=dict)
    patterns: Mapping[str, Pattern] = field(default_factory=dict)
    shared: Mapping[str, str | Field] = field(default_factory=dict)
    legacy_top_level: bool = False
    legacy_warning: Callable[[str], None] | None = None
    finalize: Callable[[Any, Context], Any] | None = None
    docs: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.package not in _toml.PACKAGES:
            raise ConfigurationError(
                f"unknown package {self.package!r}; choose from {', '.join(sorted(_toml.PACKAGES))}"
            )
        if "default" not in self.base:
            raise ConfigurationError(f"Schema {self.package!r}: base must contain 'default'")
        unknown = set(self.shared) - set(SHARED_NAMES)
        if unknown:
            raise ConfigurationError(
                f"Schema {self.package!r}: unknown shared setting(s) "
                f"{', '.join(sorted(unknown))}; choose from {', '.join(SHARED_NAMES)}"
            )
        for key, value in self.patterns.items():
            if key != value.prefix:
                raise ConfigurationError(
                    f"Schema {self.package!r}: pattern key {key!r} != prefix {value.prefix!r}"
                )
        for key in self.fields:
            if not key or any(not part for part in key.split(".")):
                raise ConfigurationError(f"Schema {self.package!r}: bad field key {key!r}")

    # ---- building

    def build(
        self,
        data: Mapping[str, Any],
        *,
        source: str = "<dict>",
        base_dir: str | Path | None = None,
    ) -> Any:
        """The target object for already-parsed TOML ``data``."""
        directory = Path(base_dir).expanduser().absolute() if base_dir is not None else None
        if not isinstance(data, Mapping):
            raise ConfigurationError(f"{source}: settings must be a table")
        table, moved = self._own_table(data, source)
        if moved:
            self._warn(source, moved)
        updates: list[tuple[str, Any]] = []
        target = self._base(data, source)
        updates.extend(self._shared(data, source, directory))
        root = Context(source, directory, f"[{self.package}]")
        updates.extend(self._walk(table, (), root))
        target = _apply(target, updates, self.package)
        if self.finalize is not None:
            target = self.finalize(target, Context(source, directory, ""))
        return target

    def load(self, path: str | Path | None = None) -> Any:
        """Build from ``path``, or ``econ-viz.toml`` in the working directory; it must exist."""
        file = Path(path) if path is not None else find()
        if file is None:
            raise ConfigurationError(f"config file not found: {FILE_NAME}")
        return self.build(read(file), source=str(file), base_dir=file.parent)

    def discover(self, directory: str | Path | None = None) -> Any:
        """Build from ``econ-viz.toml`` in ``directory`` if present, else the defaults."""
        file = find(directory)
        if file is None:
            return self.build({}, source="<defaults>")
        return self.build(read(file), source=str(file), base_dir=file.parent)

    def config_class(self, name: str = "Config") -> type[ConfigBase]:
        """A ``Config`` class for this schema; a package may subclass it."""
        return type(name, (ConfigBase,), {"schema": self, "_active": None, "__slots__": ()})

    def template(self) -> str:
        """A commented ``[<package>]`` section listing every key with its default."""
        default = self.base["default"]()
        sections: dict[str, list[str]] = {}
        for key, item in self.fields.items():
            *parents, last = key.split(".")
            section = ".".join([self.package, *parents])
            current = _dotted_get(default, item.attr)
            line = f"# {last} = {_toml_value(current)}"
            notes = [self.docs[key]] if key in self.docs else []
            if current is None:
                notes.append("(no default)")
            if notes:
                line += f"  # {' '.join(notes)}"
            sections.setdefault(section, []).append(line)
        for prefix in self.patterns:
            section = f"{self.package}.{prefix}.<name>"
            doc = self.docs.get(prefix)
            sections.setdefault(section, []).append(f"# {doc}" if doc else "# ...")
        if not sections:
            sections[self.package] = []
        blocks = []
        for section, lines in sections.items():
            blocks.append("\n".join([f"# [{section}]", *lines]))
        return "\n\n".join(blocks) + "\n"

    # ---- steps of build()

    def _own_table(
        self, data: Mapping[str, Any], source: str
    ) -> tuple[Mapping[str, Any], list[str]]:
        """This package's table, with legacy top-level keys merged in, and what moved."""
        table = data.get(self.package, {})
        if not isinstance(table, Mapping):
            raise ConfigurationError(f"{source}: [{self.package}] must be a table")
        legacy: dict[str, Any] = {}
        moved: list[str] = []
        firsts = self._first_segments()
        for key, value in data.items():
            if key in _toml.PACKAGES:
                continue
            if key in _SHARED_KEYS:
                if not isinstance(value, Mapping):
                    raise ConfigurationError(f"{source}: [{key}] must be a table")
                for sub, sub_value in value.items():
                    if sub in _SHARED_KEYS[key]:
                        continue
                    if self.legacy_top_level and f"{key}.{sub}" in self._known(key):
                        legacy.setdefault(key, {})[sub] = sub_value
                        moved.append(f"[{key}] {sub} -> [{self.package}.{key}] {sub}")
                    elif self.legacy_top_level or key != "color":
                        choices = sorted(_SHARED_KEYS[key] | self._subkeys(key))
                        raise ConfigurationError(
                            f"{source}: [{key}] unknown key {sub!r}{_unknown(sub, choices)}"
                        )
                continue
            if key in SHARED_SECTIONS:
                continue
            if self.legacy_top_level and key in firsts:
                legacy[key] = value
                moved.append(f"[{key}] -> [{self.package}.{key}]")
                continue
            if not self.legacy_top_level and key in LEGACY_SECTIONS:
                continue
            choices = sorted(
                SHARED_SECTIONS | _toml.PACKAGES | (firsts if self.legacy_top_level else set())
            )
            raise ConfigurationError(
                f"{source}: unknown top-level key {key!r}{_unknown(key, choices)}"
            )
        if not legacy:
            return table, moved
        return _merge(legacy, table), moved

    def _warn(self, source: str, moved: list[str]) -> None:
        message = (
            f"{source}: {self.package} settings at the top level are deprecated and stop "
            f"working in 3.0; move them under [{self.package}]: {'; '.join(moved)}"
        )
        if self.legacy_warning is not None:
            self.legacy_warning(message)
        else:
            warnings.warn(message, FutureWarning, stacklevel=3)

    def _base(self, data: Mapping[str, Any], source: str) -> Any:
        name = data.get("base", "default")
        if not isinstance(name, str):
            raise ConfigurationError(f"{source}: base must be a string, got {name!r}")
        if name not in self.base:
            names = sorted(self.base)
            raise ConfigurationError(
                f"{source}: base {name!r} is not a built-in {self.package} theme; "
                f"choose from {', '.join(names)}{_hint(name, names, prefix='; ')}"
            )
        return self.base[name]()

    def _shared(
        self, data: Mapping[str, Any], source: str, directory: Path | None
    ) -> list[tuple[str, Any]]:
        settings = shared_settings(
            data, base_dir=directory if directory is not None else Path.cwd(), source=source
        )
        values = {
            "font": settings.font,
            "fonts": settings.fonts,
            "math_font": settings.math_font,
            "background": settings.background,
            "axis": settings.axis,
            "label": settings.label,
        }
        updates = []
        for name, target in self.shared.items():
            value = values[name]
            if value is None:
                continue
            location = "[font]" if name in ("font", "math_font") else f"[{name}]"
            key = {"font": "text", "math_font": "math"}.get(name, name)
            if name in SHARED_COLORS:
                location = "[color]"
                if not isinstance(value, str) or not _is_color(value):
                    raise ConfigurationError(
                        _message(source, location, f"{key} must be a colour, got {value!r}")
                    )
            if isinstance(target, Field):
                ctx = Context(source, directory, location)
                updates.append((target.attr, target.convert(value, ctx, key)))
            else:
                updates.append((target, value))
        return updates

    def _walk(
        self, table: Mapping[str, Any], parts: tuple[str, ...], root: Context
    ) -> list[tuple[str, Any]]:
        location = f"[{'.'.join([self.package, *parts])}]"
        ctx = Context(root.source, root.base_dir, location)
        updates: list[tuple[str, Any]] = []
        for key, value in table.items():
            dotted = ".".join([*parts, key])
            if dotted in self.fields:
                item = self.fields[dotted]
                updates.append((item.attr, item.convert(value, ctx, key)))
            elif dotted in self.patterns:
                if not isinstance(value, Mapping):
                    raise ctx.error(f"{key} must be a table")
                updates.extend(self._pattern(self.patterns[dotted], value, root))
            elif self._is_section(dotted):
                if not isinstance(value, Mapping):
                    raise ctx.error(f"{key} must be a table")
                updates.extend(self._walk(value, (*parts, key), root))
            else:
                choices = sorted(self._next_segments(parts))
                raise ctx.error(f"unknown key {key!r}{_unknown(key, choices)}")
        return updates

    def _pattern(
        self, item: Pattern, tables: Mapping[str, Any], root: Context
    ) -> list[tuple[str, Any]]:
        updates: list[tuple[str, Any]] = []
        for name, table in tables.items():
            if not isinstance(table, Mapping):
                where = f"[{self.package}.{item.prefix}]"
                raise _located(_message(root.source, where, f"{name} must be a table"))
            ctx = Context(root.source, root.base_dir, f"[{self.package}.{item.prefix}.{name}]")
            try:
                result = item.convert(name, table, ctx)
            except ConfigurationError as error:
                raise _relocated(error, ctx, "") from None
            updates.extend(dict(result).items())
        return updates

    # ---- key bookkeeping

    def _keys(self) -> list[str]:
        return [*self.fields, *self.patterns]

    def _first_segments(self) -> set[str]:
        return {key.split(".")[0] for key in self._keys()}

    def _known(self, section: str) -> set[str]:
        return {key for key in self.fields if key.startswith(section + ".")}

    def _subkeys(self, section: str) -> set[str]:
        return {key.split(".")[1] for key in self._known(section) if key.count(".") >= 1}

    def _is_section(self, dotted: str) -> bool:
        return any(key.startswith(dotted + ".") for key in self._keys())

    def _next_segments(self, parts: tuple[str, ...]) -> set[str]:
        depth = len(parts)
        names = set()
        for key in self._keys():
            split = key.split(".")
            if len(split) > depth and tuple(split[:depth]) == parts:
                names.add(split[depth])
        return names
