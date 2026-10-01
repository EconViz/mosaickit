from collections.abc import Mapping

from mosaickit.errors import ConfigurationError
from mosaickit.themes.builtins import default
from mosaickit.themes.theme import StyleBundle, Theme


class ThemeRegistry:
    def __init__(self) -> None:
        self._themes = {default.name: default}

    def register(self, theme: Theme) -> None:
        if theme.name in self._themes:
            raise ConfigurationError(f"Theme already registered: {theme.name!r}")
        self._themes[theme.name] = theme

    def get(self, name: str) -> Theme:
        try:
            return self._themes[name]
        except KeyError as exc:
            raise ConfigurationError(f"Unknown theme: {name!r}") from exc

    def register_roles(self, name: str, roles: Mapping[str, StyleBundle]) -> Theme:
        for role in roles:
            if "." not in role:
                raise ConfigurationError(f"Domain role must be dotted: {role!r}")
        theme = self.get(name).with_roles(**roles)
        self._themes[name] = theme
        return theme
