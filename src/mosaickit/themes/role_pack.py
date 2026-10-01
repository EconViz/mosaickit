from dataclasses import fields, is_dataclass
from typing import ClassVar, Protocol

from mosaickit.errors import ConfigurationError
from mosaickit.themes.theme import StyleBundle


class RolePack(Protocol):
    _namespace: ClassVar[str]


def expand_roles(pack: RolePack) -> dict[str, StyleBundle]:
    if not is_dataclass(pack):
        raise ConfigurationError("RolePack must be a dataclass")
    if not pack._namespace or not all(pack._namespace.split(".")):
        raise ConfigurationError("RolePack requires a non-empty namespace")
    return {
        f"{pack._namespace}.{field.name.replace('_', '.')}": value
        for field in fields(pack)
        if (value := getattr(pack, field.name)) is not None
    }
