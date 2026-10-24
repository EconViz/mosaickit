"""The settings file every EconViz diagram package reads: ``econ-viz.toml``.

One file styles every package. The top level holds what all diagrams share, and each
package keeps its own settings in one table named after it::

    base = "default"          # each package's built-in theme to start from

    [font]
    text = "serif"            # generic font: sans, serif or mono
    math = "fonts/math.otf"   # math font file

    [fonts]                   # font files that replace a generic font
    serif = ["fonts/Regular.otf", "fonts/Bold.otf"]

    [color]
    background = "#ffffff"
    axis = "#1a1a1a"
    label = "#1a1a1a"         # text

    [principle.color]         # one package's own settings
    demand = "#8c8c8c"

A package does not parse the file itself. It declares a :class:`Schema` (its built-in
themes, the keys of its table and the attributes they set) and gets a ``Config`` class
from :meth:`Schema.config_class`. mosaickit reads the file, checks every value, resolves
relative paths against the file's directory, reports mistakes as
:class:`~mosaickit.ConfigurationError` with the file and table they are in, and writes
the commented template of each table.

The lower-level readers of the shared sections, :func:`shared_settings` and
:func:`package_table`, stay available.

Per-figure label overrides
--------------------------
The shared part of the file can also move single labels of single figures, so a tool can
store "this label of this figure was dragged" without touching the user's Python code::

    [figure.tax_welfare.label."market.welfare.dwl.label"]
    top = "12pt"
    right = "8pt"

``figure.<stem>`` is the stem of the output file (``tax_welfare`` for
``principle/tax_welfare.svg``); the quoted key is the id of the label layer; ``top``,
``bottom``, ``left`` and ``right`` are lengths (a number of points or a string in ``pt``,
``mm``, ``cm``, ``in``; ``em`` is rejected because the file has no font size) that combine
like :func:`~mosaickit.styles.nudge.nudge_from`. :func:`figure_labels` parses them,
:func:`figure_overrides` reads the active ones, and ``Canvas.save`` / ``CanvasGrid.save`` apply
them to the file they write. Activating a package config with ``Config.use()`` (or
:func:`use`) activates the overrides of the file it was read from.
"""

from __future__ import annotations

import difflib
import json
import math
import re
import sys
import warnings
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, is_dataclass, replace
from importlib import metadata
from pathlib import Path
from types import MappingProxyType
from typing import Any, ClassVar

from mosaickit import label_overrides
from mosaickit.errors import ConfigurationError
from mosaickit.label_overrides import NO_FIGURES as _NO_FIGURES
from mosaickit.label_overrides import FigureLabels
from mosaickit.palette import DEFAULT_PALETTE
from mosaickit.styles.nudge import POINTS_PER_UNIT, Nudge, parse_length
from mosaickit.text_fonts import GENERIC_FONTS, TextFonts

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on Python 3.10 only
    import tomli as tomllib

FILE_NAME = "econ-viz.toml"
# Every EconViz package, installed or not; each owns the table named after it.
PACKAGES = frozenset({"utility", "principle", "micro", "macro", "trade", "dsge", "game"})
# The tables that belong to one package each; a package skips the others' tables.
PACKAGE_TABLES = PACKAGES
# The top-level keys every package understands.
SHARED_SECTIONS = frozenset({"base", "font", "fonts", "color", "figure"})
SHARED_COLORS = ("background", "axis", "label")
# The shared settings a Schema can map onto its target.
SHARED_NAMES = ("font", "fonts", "math_font", "background", "axis", "label")
# utility-viz's top-level tables before 2.0 (deprecated, removed in 3.0). Other packages
# skip them, as they skip the extra keys utility-viz kept in [color].
LEGACY_SECTIONS = frozenset({"stroke", "marker", "label", "fill", "legend"})
ENTRY_POINT_GROUP = "econviz.config"

_SHARED_KEYS: Mapping[str, frozenset[str]] = {
    "font": frozenset({"text", "math"}),
    "fonts": frozenset(GENERIC_FONTS),
    "color": frozenset(SHARED_COLORS),
}
_HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})")


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
    if name not in PACKAGES:
        raise ConfigurationError(f"{name!r} is not a package table; choose from {sorted(PACKAGES)}")
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


# ------------------------------------------------------------------ figure label overrides

LABEL_SIDES = ("top", "bottom", "left", "right")
_BARE_KEY = re.compile(r"[A-Za-z0-9_-]+")


def figure_labels(data: Mapping[str, Any], *, source: str = "config") -> FigureLabels:
    """The ``[figure.<stem>.label."<id>"]`` overrides of parsed TOML ``data``.

    Returns ``{stem: {label id: Nudge}}``, empty when the file has no ``[figure]`` table.
    Each table sets ``top``, ``bottom``, ``left`` and ``right`` as lengths (a number of
    points, or ``"12pt"``, ``"2mm"``, ``"0.5cm"``, ``"0.1in"``; ``em`` is rejected because
    the file has no font size). ``dy = top - bottom`` and ``dx = right - left``, as for
    :func:`~mosaickit.styles.nudge.nudge_from`. An empty table is a zero nudge, which
    cancels the label's own. Anything malformed raises ``ConfigurationError`` naming the
    file and the table; label ids that no figure has are not checked here.
    """
    figure = data.get("figure")
    if figure is None:
        return _NO_FIGURES
    if not isinstance(figure, Mapping):
        raise ConfigurationError(f"{source}: [figure] must be a table")
    convert = length("nudge").convert
    stems: dict[str, Mapping[str, Nudge]] = {}
    for stem, table in figure.items():
        where = f"[figure.{_toml_key(stem)}]"
        root = Context(source, None, where)
        if not isinstance(table, Mapping):
            raise root.error("must be a table")
        for key in table:
            if key != "label":
                raise root.error(f"unknown key {key!r}{_unknown(key, ['label'])}")
        labels = table.get("label", {})
        if not isinstance(labels, Mapping):
            raise Context(source, None, where).error("label must be a table")
        nudges: dict[str, Nudge] = {}
        for label_id, sides in labels.items():
            ctx = Context(source, None, f"{where[:-1]}.label.{_toml_key(label_id)}]")
            if not isinstance(sides, Mapping):
                raise Context(source, None, f"{where[:-1]}.label]").error(
                    f"{label_id!r} must be a table"
                )
            for key in sides:
                if key not in LABEL_SIDES:
                    raise ctx.error(f"unknown key {key!r}{_unknown(key, LABEL_SIDES)}")
            amounts = {side: convert(sides.get(side, 0), ctx, side) for side in LABEL_SIDES}
            nudges[label_id] = Nudge(
                dx=amounts["right"] - amounts["left"], dy=amounts["top"] - amounts["bottom"]
            )
        stems[stem] = MappingProxyType(nudges)
    return MappingProxyType(stems)


def _toml_key(key: str) -> str:
    return key if _BARE_KEY.fullmatch(key) else json.dumps(key, ensure_ascii=False)


def figure_overrides(stem: str | None = None) -> Any:
    """The active per-figure label overrides, read-only.

    With no ``stem``: ``{stem: {label id: Nudge}}`` for every figure. With a ``stem``:
    ``{label id: Nudge}`` for that figure, empty when it has none. Overrides become active
    through ``Config.use()`` of any package config read from a file (or :func:`use`), or
    :func:`activate_figure_overrides`; until then nothing is active.
    """
    return label_overrides.active() if stem is None else label_overrides.active_for(stem)


def activate_figure_overrides(figures: FigureLabels | None) -> None:
    """Make ``figures`` (as :func:`figure_labels` returns) the active overrides, replacing any.

    ``None`` or an empty mapping clears them.
    """
    label_overrides.activate(figures)


def clear_figure_overrides() -> None:
    """Drop the active per-figure label overrides (tests call this to start clean)."""
    label_overrides.activate(None)


# --------------------------------------------------------------------------- schema


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
        if self.package not in PACKAGES:
            raise ConfigurationError(
                f"unknown package {self.package!r}; choose from {', '.join(sorted(PACKAGES))}"
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
            if key in PACKAGES:
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
                SHARED_SECTIONS | PACKAGES | (firsts if self.legacy_top_level else set())
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


# --------------------------------------------------------------------------- Config


class ConfigBase:
    """Base of the classes :meth:`Schema.config_class` makes.

    ``config.value`` is the built target; other attributes are read from it, so
    ``config.theme`` works when the target has ``theme``.
    """

    __slots__ = ("figure_labels", "value")
    schema: ClassVar[Schema]
    _active: ClassVar[ConfigBase | None]

    def __init__(self, value: Any = None, *, figure_labels: FigureLabels | None = None) -> None:
        if value is None:
            value = self.schema.build({}, source="<defaults>")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "figure_labels", figure_labels)

    @classmethod
    def load(cls, path: str | Path | None = None) -> Any:
        """Read ``path``, or ``econ-viz.toml`` in the working directory (which must exist)."""
        file = Path(path) if path is not None else find()
        if file is None:
            raise ConfigurationError(f"config file not found: {FILE_NAME}")
        return cls._from_file(file)

    @classmethod
    def discover(cls, directory: str | Path | None = None) -> Any:
        """Read ``econ-viz.toml`` in ``directory`` if present, else the defaults."""
        file = find(directory)
        if file is None:
            return cls(cls.schema.build({}, source="<defaults>"), figure_labels=_NO_FIGURES)
        return cls._from_file(file)

    @classmethod
    def _from_file(cls, file: Path) -> Any:
        return cls.from_dict(read(file), source=str(file), base_dir=file.parent)

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        *,
        source: str = "<dict>",
        base_dir: str | Path | None = None,
    ) -> Any:
        """Build from already-parsed TOML data."""
        return cls(
            cls.schema.build(data, source=source, base_dir=base_dir),
            figure_labels=figure_labels(data, source=source),
        )

    def use(self) -> Any:
        """Make this the package's active config; returns ``self``.

        A config read from a file (``load``, ``discover``, ``from_dict``) also makes that
        file's ``[figure.*]`` label overrides the active ones (:func:`figure_overrides`),
        replacing those of any earlier activation, also when the file has none. A config
        made directly with ``Config(value)`` has no file and leaves them alone.
        """
        _owner(type(self))._active = self
        if self.figure_labels is not None:
            label_overrides.activate(self.figure_labels, _owner(type(self)))
        return self

    @classmethod
    def reset(cls) -> None:
        """Clear the package's active config, and the label overrides it activated."""
        owner = _owner(cls)
        owner._active = None
        if label_overrides.owned_by(owner):
            label_overrides.activate(None)

    @classmethod
    def active(cls) -> Any:
        """The package's active config, or ``None``."""
        return _owner(cls)._active

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") or name == "value":
            raise AttributeError(name)
        return getattr(object.__getattribute__(self, "value"), name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"{type(self).__name__} is read-only")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConfigBase) or _owner(type(other)) is not _owner(type(self)):
            return NotImplemented
        return bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash((_owner(type(self)), self.value))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.value!r})"


def _owner(cls: type) -> type[ConfigBase]:
    """The class config_class() made, which holds the active config for subclasses too."""
    for klass in cls.__mro__:
        if "schema" in klass.__dict__:
            return klass
    raise TypeError(f"{cls.__name__} was not made by Schema.config_class()")


# --------------------------------------------------------------------------- registry

_REGISTRY: dict[str, Schema] = {}


def register(schema: Schema) -> Schema:
    """Add ``schema`` to the registry; registering a package again replaces it."""
    _REGISTRY[schema.package] = schema
    return schema


def registered() -> Mapping[str, Schema]:
    """The registered schemas by package."""
    return MappingProxyType(dict(_REGISTRY))


def load(path: str | Path | None = None) -> Mapping[str, Any]:
    """``{package: built target}`` for every registered package, from one file."""
    file = Path(path) if path is not None else find()
    if file is None:
        raise ConfigurationError(f"config file not found: {FILE_NAME}")
    data = read(file)
    return {
        package: schema.build(data, source=str(file), base_dir=file.parent)
        for package, schema in _REGISTRY.items()
    }


def use(path: str | Path | None = None) -> None:
    """Load and activate the config of every package installed under ``econviz.config``."""
    for entry in metadata.entry_points(group=ENTRY_POINT_GROUP):
        config = entry.load()
        config.load(path).use()


# --------------------------------------------------------------------------- helpers


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


def _merge(low: Mapping[str, Any], high: Mapping[str, Any]) -> dict[str, Any]:
    """``low`` updated by ``high``, table by table."""
    merged = dict(low)
    for key, value in high.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class _Node:
    __slots__ = ("children", "has_value", "value")

    def __init__(self) -> None:
        self.has_value = False
        self.value: Any = None
        self.children: dict[str, _Node] = {}


def _apply(target: Any, updates: Iterable[tuple[str, Any]], package: str) -> Any:
    """Set dotted attributes in order, rebuilding each frozen dataclass once."""
    root = _Node()
    for attr, value in updates:
        node = root
        for part in attr.split("."):
            node = node.children.setdefault(part, _Node())
        node.has_value, node.value = True, value
        node.children.clear()  # a later whole value replaces earlier nested ones
    return _rebuild(target, root, package, "")


def _rebuild(obj: Any, node: _Node, package: str, where: str) -> Any:
    if not node.children:
        return obj
    if not is_dataclass(obj) or isinstance(obj, type):
        raise ConfigurationError(
            f"Schema {package!r}: cannot set {', '.join(node.children)} on "
            f"{where or 'the target'}, which is not a dataclass instance"
        )
    changes = {}
    for name, child in node.children.items():
        dotted = f"{where}.{name}" if where else name
        if not hasattr(obj, name):
            raise ConfigurationError(f"Schema {package!r}: target has no attribute {dotted!r}")
        current = child.value if child.has_value else getattr(obj, name)
        changes[name] = _rebuild(current, child, package, dotted)
    try:
        return replace(obj, **changes)
    except (TypeError, ValueError) as error:
        raise ConfigurationError(
            f"Schema {package!r}: cannot set {where or 'the target'}: {error}"
        ) from error


def _dotted_get(obj: Any, attr: str) -> Any:
    for part in attr.split("."):
        obj = getattr(obj, part, None)
    return obj


def _toml_value(value: Any) -> str:
    if hasattr(value, "to_hex"):
        value = value.to_hex()
    if isinstance(value, (bool, str)) or (isinstance(value, (int, float)) and math.isfinite(value)):
        return _toml_scalar(value)
    if isinstance(value, (list, tuple)) and all(
        isinstance(item, (bool, str, int, float)) for item in value
    ):
        return "[" + ", ".join(_toml_scalar(item) for item in value) + "]"
    return "..."


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return repr(value)


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


def _path(value: str, directory: Path | None) -> str:
    resolved = Path(value).expanduser()
    if directory is not None and not resolved.is_absolute():
        resolved = directory / resolved
    return str(resolved)


__all__ = [
    "ENTRY_POINT_GROUP",
    "FILE_NAME",
    "LABEL_SIDES",
    "LEGACY_SECTIONS",
    "PACKAGES",
    "PACKAGE_TABLES",
    "SHARED_COLORS",
    "SHARED_NAMES",
    "SHARED_SECTIONS",
    "ConfigBase",
    "Context",
    "Field",
    "FigureLabels",
    "Pattern",
    "Schema",
    "SharedSettings",
    "activate_figure_overrides",
    "boolean",
    "choice",
    "clear_figure_overrides",
    "color",
    "figure_labels",
    "figure_overrides",
    "find",
    "length",
    "load",
    "number",
    "package_table",
    "path",
    "pattern",
    "positive",
    "read",
    "register",
    "registered",
    "shared_settings",
    "string",
    "transform",
    "use",
]
