"""Named color palettes. Themes take their colors from a palette by name."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from mosaickit.colors import Color
from mosaickit.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class Palette:
    name: str
    colors: Mapping[str, Color]

    def __post_init__(self) -> None:
        colors = {}
        for key, value in self.colors.items():
            if not isinstance(key, str) or not key:
                raise ConfigurationError(f"Palette color names must be non-empty: {key!r}")
            colors[key] = value if isinstance(value, Color) else Color.from_hex(value)
        object.__setattr__(self, "colors", MappingProxyType(colors))

    def __getitem__(self, name: str) -> Color:
        try:
            return self.colors[name]
        except KeyError as exc:
            raise ConfigurationError(f"Palette {self.name!r} has no color {name!r}") from exc

    def __contains__(self, name: object) -> bool:
        return name in self.colors

    def __hash__(self) -> int:
        return hash((self.name, tuple(self.colors.items())))


_DEFAULT_HEX = {
    # Neutrals: text, axes, guides, default fills.
    "grey-900": "#222222",
    "grey-800": "#333333",
    "grey-600": "#666666",
    "grey-400": "#999999",
    "grey-200": "#CCCCCC",
    "grey-100": "#E6E6E6",
    "white": "#FFFFFF",
    # Hues.
    "blue": "#01A2D9",
    "red": "#E3120B",
    "teal": "#00887D",
}

DEFAULT_PALETTE = Palette(
    "default", {name: Color.from_hex(value) for name, value in _DEFAULT_HEX.items()}
)
