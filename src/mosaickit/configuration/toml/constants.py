"""Names, keys and file conventions of ``econ-viz.toml``."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit.text_fonts import GENERIC_FONTS

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
