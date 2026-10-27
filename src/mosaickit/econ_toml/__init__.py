"""Compatibility package for :mod:`mosaickit.configuration.toml`."""

from __future__ import annotations

import importlib
import sys

from mosaickit.configuration.toml import *  # noqa: F403
from mosaickit.configuration.toml import __all__ as __all__
from mosaickit.configuration.toml import metadata as metadata
from mosaickit.configuration.toml import tomllib as tomllib

for _name in (
    "_apply",
    "_helpers",
    "config",
    "constants",
    "fields",
    "figures",
    "registry",
    "schema",
    "shared",
):
    _module = importlib.import_module(f"mosaickit.configuration.toml.{_name}")
    sys.modules[f"{__name__}.{_name}"] = _module
    globals()[_name] = _module

del _module, _name
