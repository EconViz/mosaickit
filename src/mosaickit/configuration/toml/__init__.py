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

from importlib import metadata  # noqa: F401  # patched by tests and callers as econ_toml.metadata

from mosaickit.configuration.label_overrides import FigureLabels
from mosaickit.configuration.toml.config import ConfigBase
from mosaickit.configuration.toml.constants import (
    ENTRY_POINT_GROUP,
    FILE_NAME,
    LEGACY_SECTIONS,
    PACKAGE_TABLES,
    PACKAGES,
    SHARED_COLORS,
    SHARED_NAMES,
    SHARED_SECTIONS,
)
from mosaickit.configuration.toml.fields import (
    Context,
    Field,
    Pattern,
    boolean,
    choice,
    color,
    length,
    number,
    path,
    pattern,
    positive,
    string,
    transform,
)
from mosaickit.configuration.toml.figures import (
    LABEL_SIDES,
    activate_figure_overrides,
    clear_figure_overrides,
    figure_labels,
    figure_overrides,
)
from mosaickit.configuration.toml.registry import load, register, registered, use
from mosaickit.configuration.toml.schema import Schema
from mosaickit.configuration.toml.shared import (
    SharedSettings,
    find,
    package_table,
    read,
    shared_settings,
    tomllib,  # noqa: F401  # tests and callers read econ_toml.tomllib
)

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
