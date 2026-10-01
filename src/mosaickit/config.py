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
from mosaickit.errors import ConfigurationError
from mosaickit.styles import Fill, LegendStyle, Marker, Stroke, TextStyle
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

    def __post_init__(self) -> None:
        checked = Theme("config", self.role_overrides)
        object.__setattr__(self, "role_overrides", MappingProxyType(dict(checked.roles)))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, source: str = "<dict>") -> Config:
        try:
            unknown = set(data) - {"theme", "canvas", "renderer", "styles"}
            if unknown:
                raise ConfigurationError(f"Unknown configuration keys: {sorted(unknown)}")
            if data.get("theme", "default") != "default":
                raise ConfigurationError(
                    "TOML theme must be 'default'; pass custom Theme in Python"
                )
            if data.get("renderer", "matplotlib") != "matplotlib":
                raise ConfigurationError("TOML renderer must be 'matplotlib'")
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
                    try:
                        patches[name] = types[name](**values)
                    except (TypeError, ValueError) as exc:
                        raise ConfigurationError(f"styles.{role}.{name}: {exc}") from exc
                styles[role] = StyleBundle(**patches)
            return cls(
                canvas_spec=CanvasSpec(**data.get("canvas", {})),
                renderer=data.get("renderer", "matplotlib"),
                role_overrides=styles,
            )
        except (TypeError, ValueError, AttributeError) as exc:
            raise ConfigurationError(f"{source}: {exc}") from exc

    @classmethod
    def load(cls, path: str | Path) -> Config:
        path = Path(path)
        try:
            with path.open("rb") as stream:
                return cls.from_dict(tomllib.load(stream), source=str(path))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ConfigurationError(f"{path}: {exc}") from exc


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
