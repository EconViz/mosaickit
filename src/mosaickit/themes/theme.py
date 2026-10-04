"""Immutable namespaced theme values."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from types import MappingProxyType

from mosaickit.errors import ConfigurationError
from mosaickit.styles import Fill, LegendStyle, Marker, Stroke, TextStyle


@dataclass(frozen=True, slots=True)
class StyleBundle:
    stroke: Stroke | None = None
    fill: Fill | None = None
    marker: Marker | None = None
    text: TextStyle | None = None
    legend: LegendStyle | None = None

    def __post_init__(self) -> None:
        for name, expected in (
            ("stroke", Stroke),
            ("fill", Fill),
            ("marker", Marker),
            ("text", TextStyle),
            ("legend", LegendStyle),
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, expected):
                raise ConfigurationError(f"StyleBundle.{name} requires {expected.__name__}")

    def merged_over(self, base: StyleBundle) -> StyleBundle:
        result = {}
        for field in fields(self):
            top, bottom = getattr(self, field.name), getattr(base, field.name)
            result[field.name] = (
                bottom if top is None else top if bottom is None else top.merged_over(bottom)
            )
        return StyleBundle(**result)


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    roles: Mapping[str, StyleBundle]
    defaults: StyleBundle = StyleBundle()

    def __post_init__(self) -> None:
        if not isinstance(self.defaults, StyleBundle):
            raise ConfigurationError("Theme.defaults requires a StyleBundle")
        for role, bundle in self.roles.items():
            if not isinstance(role, str) or not all(part for part in role.split(".")):
                raise ConfigurationError(f"Invalid role: {role!r}")
            if not isinstance(bundle, StyleBundle):
                raise ConfigurationError(f"Role {role!r} requires a StyleBundle")
        object.__setattr__(self, "roles", MappingProxyType(dict(self.roles)))

    def __hash__(self) -> int:
        return hash((self.name, tuple(sorted(self.roles.items())), self.defaults))

    def with_roles(self, **patch: StyleBundle) -> Theme:
        roles = dict(self.roles)
        for name, value in patch.items():
            roles[name] = value.merged_over(roles.get(name, StyleBundle()))
        return Theme(self.name, roles, defaults=self.defaults)

    def resolve(self, role: str, *, fallback_category: str) -> StyleBundle:
        from mosaickit.themes.resolution import resolve

        return resolve(self, role, fallback_category=fallback_category)
