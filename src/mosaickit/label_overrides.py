"""The label overrides in force for this process, keyed by figure stem.

``econ-viz.toml`` can move single labels of single figures (``[figure.<stem>.label."<id>"]``,
parsed by :mod:`mosaickit.econ_toml`). What it read is kept here, as plain data, so saving a
canvas can look it up without knowing anything about configuration files.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from mosaickit.styles.nudge import Nudge

FigureLabels = Mapping[str, Mapping[str, Nudge]]
"""Figure stem -> label layer id -> the nudge that replaces that label's own."""

NO_FIGURES: FigureLabels = MappingProxyType({})

_active: FigureLabels = NO_FIGURES
_owner: object | None = None


def active() -> FigureLabels:
    """All active overrides: ``{stem: {label id: Nudge}}``."""
    return _active


def active_for(stem: str) -> Mapping[str, Nudge]:
    """The active overrides of the figure ``stem``: ``{label id: Nudge}``, maybe empty."""
    return _active.get(stem, MappingProxyType({}))


def activate(figures: FigureLabels | None, owner: object | None = None) -> None:
    """Make ``figures`` the active overrides; ``None`` or empty clears them.

    ``owner`` marks who activated them, so that one package resetting its config does not
    drop overrides another activated.
    """
    global _active, _owner
    _active = figures if figures else NO_FIGURES
    _owner = owner if figures else None


def owned_by(owner: object) -> bool:
    """Whether the active overrides were activated by ``owner``."""
    return _owner is owner


__all__ = ["NO_FIGURES", "FigureLabels", "activate", "active", "active_for", "owned_by"]
