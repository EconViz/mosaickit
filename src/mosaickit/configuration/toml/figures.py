"""Per-figure label overrides: ``[figure.<stem>.label."<id>"]``."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from mosaickit.configuration import label_overrides
from mosaickit.configuration.label_overrides import NO_FIGURES as _NO_FIGURES
from mosaickit.configuration.label_overrides import FigureLabels
from mosaickit.configuration.toml._helpers import _unknown
from mosaickit.configuration.toml.fields import Context, length
from mosaickit.errors import ConfigurationError
from mosaickit.styles.nudge import Nudge

LABEL_SIDES = ("top", "bottom", "left", "right")
_BARE_KEY = re.compile(r"[A-Za-z0-9_-]+")


def figure_labels(data: Mapping[str, Any], *, source: str = "config") -> FigureLabels:
    """The ``[figure.<stem>.label."<id>"]`` overrides of parsed TOML ``data``.

    Returns ``{stem: {label id: Nudge}}``, empty when the file has no ``[figure]`` table.
    Each table sets ``top``, ``bottom``, ``left`` and ``right`` as lengths (a number of
    points, or ``"12pt"``, ``"2mm"``, ``"0.5cm"``, ``"0.1in"``; ``em`` is rejected because
    the file has no font size). ``dy = top - bottom`` and ``dx = right - left``, as for
    :func:`~mosaickit.styles.nudge.nudge_from`. An empty table is a zero nudge, which
    cancels the label's own. Anything malformed raises ``ConfigurationError`` naming the
    file and the table; label ids that no figure has are not checked here.
    """
    figure = data.get("figure")
    if figure is None:
        return _NO_FIGURES
    if not isinstance(figure, Mapping):
        raise ConfigurationError(f"{source}: [figure] must be a table")
    convert = length("nudge").convert
    stems: dict[str, Mapping[str, Nudge]] = {}
    for stem, table in figure.items():
        where = f"[figure.{_toml_key(stem)}]"
        root = Context(source, None, where)
        if not isinstance(table, Mapping):
            raise root.error("must be a table")
        for key in table:
            if key != "label":
                raise root.error(f"unknown key {key!r}{_unknown(key, ['label'])}")
        labels = table.get("label", {})
        if not isinstance(labels, Mapping):
            raise Context(source, None, where).error("label must be a table")
        nudges: dict[str, Nudge] = {}
        for label_id, sides in labels.items():
            ctx = Context(source, None, f"{where[:-1]}.label.{_toml_key(label_id)}]")
            if not isinstance(sides, Mapping):
                raise Context(source, None, f"{where[:-1]}.label]").error(
                    f"{label_id!r} must be a table"
                )
            for key in sides:
                if key not in LABEL_SIDES:
                    raise ctx.error(f"unknown key {key!r}{_unknown(key, LABEL_SIDES)}")
            amounts = {side: convert(sides.get(side, 0), ctx, side) for side in LABEL_SIDES}
            nudges[label_id] = Nudge(
                dx=amounts["right"] - amounts["left"], dy=amounts["top"] - amounts["bottom"]
            )
        stems[stem] = MappingProxyType(nudges)
    return MappingProxyType(stems)


def _toml_key(key: str) -> str:
    return key if _BARE_KEY.fullmatch(key) else json.dumps(key, ensure_ascii=False)


def figure_overrides(stem: str | None = None) -> Any:
    """The active per-figure label overrides, read-only.

    With no ``stem``: ``{stem: {label id: Nudge}}`` for every figure. With a ``stem``:
    ``{label id: Nudge}`` for that figure, empty when it has none. Overrides become active
    through ``Config.use()`` of any package config read from a file (or :func:`use`), or
    :func:`activate_figure_overrides`; until then nothing is active.
    """
    return label_overrides.active() if stem is None else label_overrides.active_for(stem)


def activate_figure_overrides(figures: FigureLabels | None) -> None:
    """Make ``figures`` (as :func:`figure_labels` returns) the active overrides, replacing any.

    ``None`` or an empty mapping clears them.
    """
    label_overrides.activate(figures)


def clear_figure_overrides() -> None:
    """Drop the active per-figure label overrides (tests call this to start clean)."""
    label_overrides.activate(None)
