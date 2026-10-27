"""The registry of schemas, and loading every registered or installed package at once."""

from __future__ import annotations

from collections.abc import Mapping
from importlib import metadata
from pathlib import Path
from types import MappingProxyType
from typing import Any

from mosaickit.configuration.toml.constants import ENTRY_POINT_GROUP, FILE_NAME
from mosaickit.configuration.toml.schema import Schema
from mosaickit.configuration.toml.shared import find, read
from mosaickit.errors import ConfigurationError

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
