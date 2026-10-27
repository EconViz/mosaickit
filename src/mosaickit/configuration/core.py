"""Strict runtime configuration with task-local defaults."""

from __future__ import annotations

import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from mosaickit.canvas_spec import CanvasSpec
from mosaickit.colors import Color
from mosaickit.errors import ConfigurationError
from mosaickit.math_font import MathFont
from mosaickit.palette import DEFAULT_PALETTE, Palette
from mosaickit.styles import Fill, LegendStyle, Marker, Stroke, TextStyle
from mosaickit.text_fonts import TextFonts
from mosaickit.themes import StyleBundle, Theme, default

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass(frozen=True, slots=True)
class Config:
    theme: Theme = default
    canvas_spec: CanvasSpec = CanvasSpec()
    renderer: Any = "matplotlib"
    role_overrides: Mapping[str, StyleBundle] = field(default_factory=dict)
    palette: Palette = DEFAULT_PALETTE
    math_font: MathFont | None = None
    fonts: TextFonts | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.palette, Palette):
            raise ConfigurationError("Config.palette must be a Palette")
        if self.math_font is not None and not isinstance(self.math_font, MathFont):
            raise ConfigurationError("Config.math_font must be a MathFont or None")
        if self.fonts is not None and not isinstance(self.fonts, TextFonts):
            raise ConfigurationError("Config.fonts must be a TextFonts or None")
        checked = Theme("config", self.role_overrides)
        object.__setattr__(self, "role_overrides", MappingProxyType(dict(checked.roles)))

    @classmethod
    def from_dict(
        cls, data: Mapping[str, Any], *, source: str = "<dict>", base_dir: Path | None = None
    ) -> Config:
        """Build a configuration from parsed TOML data.

        A relative ``[math] font`` path is resolved against ``base_dir`` when given.
        """
        try:
            unknown = set(data) - {
                "theme",
                "canvas",
                "renderer",
                "styles",
                "palette",
                "math",
                "fonts",
            }
            if unknown:
                raise ConfigurationError(f"Unknown configuration keys: {sorted(unknown)}")
            if data.get("theme", "default") != "default":
                raise ConfigurationError(
                    "TOML theme must be 'default'; pass custom Theme in Python"
                )
            if data.get("renderer", "matplotlib") != "matplotlib":
                raise ConfigurationError("TOML renderer must be 'matplotlib'")
            palette = _palette(data.get("palette", {}))
            styles = {}
            types = {
                "stroke": Stroke,
                "fill": Fill,
                "marker": Marker,
                "text": TextStyle,
                "legend": LegendStyle,
            }
            for role, sections in data.get("styles", {}).items():
                unknown_styles = set(sections) - types.keys()
                if unknown_styles:
                    raise ConfigurationError(
                        f"styles.{role}: unknown styles {sorted(unknown_styles)}"
                    )
                patches = {}
                for name, values in sections.items():
                    _check_color_names(values, palette, f"styles.{role}.{name}")
                    try:
                        patches[name] = types[name](**values)
                    except (TypeError, ValueError) as exc:
                        raise ConfigurationError(f"styles.{role}.{name}: {exc}") from exc
                styles[role] = StyleBundle(**patches)
            return cls(
                canvas_spec=CanvasSpec(**data.get("canvas", {})),
                renderer=data.get("renderer", "matplotlib"),
                role_overrides=styles,
                palette=palette,
                math_font=_math_font(data.get("math", {}), base_dir),
                fonts=_text_fonts(data.get("fonts", {}), base_dir),
            )
        except (TypeError, ValueError, AttributeError) as exc:
            raise ConfigurationError(f"{source}: {exc}") from exc

    @classmethod
    def load(cls, path: str | Path) -> Config:
        path = Path(path)
        try:
            with path.open("rb") as stream:
                return cls.from_dict(tomllib.load(stream), source=str(path), base_dir=path.parent)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ConfigurationError(f"{path}: {exc}") from exc


_COLOR_FIELDS = ("color", "edge_color")


def _palette(section: Any) -> Palette:
    """Layer a TOML ``[palette]`` table over the default palette."""
    if not isinstance(section, Mapping):
        raise ConfigurationError("palette must be a table of name = hex color")
    if not section:
        return DEFAULT_PALETTE
    colors: dict[str, Color] = dict(DEFAULT_PALETTE.colors)
    for name, value in section.items():
        if not name:
            raise ConfigurationError("palette: color names must be non-empty")
        try:
            colors[name] = Color.from_hex(value)
        except ConfigurationError as exc:
            raise ConfigurationError(f"palette.{name}: {exc}") from exc
    return Palette("config", colors)


def _math_font(section: Any, base_dir: Path | None) -> MathFont | None:
    """Read a TOML ``[math]`` table: ``font`` (a file path) and optional ``italic``."""
    if not isinstance(section, Mapping):
        raise ConfigurationError("math must be a table with a font path")
    unknown = set(section) - {"font", "italic"}
    if unknown:
        raise ConfigurationError(f"math: unknown keys {sorted(unknown)}")
    if "font" not in section:
        if section:
            raise ConfigurationError("math.font is required")
        return None
    font = section["font"]
    if not isinstance(font, str) or not font:
        raise ConfigurationError("math.font must be a file path")
    path = Path(font).expanduser()
    if base_dir is not None and not path.is_absolute():
        path = base_dir / path
    try:
        return MathFont(path, **({"italic": section["italic"]} if "italic" in section else {}))
    except ConfigurationError as exc:
        raise ConfigurationError(f"math: {exc}") from exc


def _text_fonts(section: Any, base_dir: Path | None) -> TextFonts | None:
    """Read a TOML ``[fonts]`` table: ``sans``, ``serif`` and ``mono``, each a list of font files.

    ``files`` is an older name for ``sans``.
    """
    if not isinstance(section, Mapping):
        raise ConfigurationError("fonts must be a table of font file lists")
    unknown = set(section) - {"sans", "serif", "mono", "files"}
    if unknown:
        raise ConfigurationError(f"fonts: unknown keys {sorted(unknown)}")
    if "files" in section and "sans" in section:
        raise ConfigurationError("fonts: files is another name for sans; give only one")
    slots: dict[str, tuple[Path, ...]] = {}
    for key, slot in (("sans", "sans"), ("files", "sans"), ("serif", "serif"), ("mono", "mono")):
        if key not in section:
            continue
        files = section[key]
        if isinstance(files, str):
            files = [files]
        if (
            not isinstance(files, list)
            or not files
            or not all(isinstance(f, str) and f for f in files)
        ):
            raise ConfigurationError(f"fonts.{key} must be a non-empty list of file paths")
        paths = []
        for name in files:
            path = Path(name).expanduser()
            if base_dir is not None and not path.is_absolute():
                path = base_dir / path
            paths.append(path)
        slots[slot] = tuple(paths)
    if not slots:
        return None
    try:
        return TextFonts(**slots)
    except ConfigurationError as exc:
        raise ConfigurationError(f"fonts: {exc}") from exc


def _check_color_names(values: Any, palette: Palette, where: str) -> None:
    """Fail at load time, naming the key, if a style table uses an unknown color name.

    Names stay names in the style; they are resolved when a render plan is built.
    """
    if not isinstance(values, Mapping):
        return
    for key in _COLOR_FIELDS:
        value = values.get(key)
        if isinstance(value, str) and not value.startswith("#") and value not in palette:
            raise ConfigurationError(
                f"{where}.{key}: unknown color {value!r}; use a #hex value or a name from [palette]"
            )


_active: ContextVar[Config | None] = ContextVar("econ_viz_config", default=None)


def current_config() -> Config:
    value = _active.get()
    return value if value is not None else Config()


@contextmanager
def use_config(config: Config) -> Iterator[Config]:
    token = _active.set(config)
    try:
        yield config
    finally:
        _active.reset(token)
