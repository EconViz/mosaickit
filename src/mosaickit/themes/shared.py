"""Shared theme tokens: one colour per role, plus size multipliers.

A shared theme assigns a colour to each of the roles in :data:`ROLES` and gives three size
multipliers. Diagram packages map their own elements to these roles (in their own code) and
build their theme objects from the tokens, so a theme name means the same look in every
package. This module is pure data plus lookup: it knows nothing about TOML, rendering or any
diagram package. There is deliberately no dark theme.

Colours are ``#RRGGBB`` or ``#RRGGBBAA`` hex strings; an alpha byte marks a translucent
companion colour (``subtle`` is the primary colour at 45 % opacity, alpha ``0x73``). Only
``background`` may also be ``None``, meaning a transparent background.

Values and their sources
------------------------

Sources: **spec** = the shared-theme spec table; **uv** = utility-viz
``utility_viz/core/themes`` (2.0.0b7); **pv** = principle-viz
``principle_viz/visuals/theme.py`` colour models.

``background`` is ``None`` (transparent, as uv's themes are today) in every theme except
manual, which is white.
``manual`` is exactly the spec's manual column (playground settings, pv ``MANUAL_COLOR_MODEL``).

============ ========= ========= ========= ========= ========= ========= =========
role         manual    default   colorbl.  monochr.  nord      paper     present.
============ ========= ========= ========= ========= ========= ========= =========
background   #ffffff   None      None      None      None      None      None
ink          #1a1a1a   #222222   #222222   #000000   #2E3440   #1A1A1A   #1A1A1A
primary      #8c8c8c   #377EB8   #377EB8   #000000   #88C0D0   #345995   #1F77B4
secondary    #1a1a1a   #4DAF4A   #4DAF4A   #000000   #A3BE8C   #4B7355   #2CA02C
constraint   #222222   #984EA3   #984EA3   #000000   #5E81AC   #5C5C5C   #9467BD
tertiary     #6e6e6e   #777777   #777777   #6E6E6E   #4C566A   #8C8C8C   #7F7F7F
accent       #1a1a1a   #E41A1C   #E41A1C   #000000   #BF616A   #8C2F39   #D62728
intervention #595959   #FF7F00   #FF7F00   #2E2E2E   #EBCB8B   #B8621B   #FF7F0E
muted        #8c8c8c   #999999   #999999   #555555   #4C566A   #8C8C8C   #7F7F7F
subtle       #b8b8b8   #377EB873 #377EB873 #00000073 #88C0D073 #34599573 #1F77B473
series.1     #8c8c8c   #FF7F00   #FF7F00   #000000   #FF7F00   #B8621B   #FF7F0E
series.2     #8c8c8c   #4DAF4A   #4DAF4A   #000000   #4DAF4A   #4B7355   #2CA02C
series.3     #8c8c8c   #A65628   #A65628   #000000   #88C0D0   #6B4226   #8C564B
fill.light   #b8b8b8   #377EB8   #377EB8   #E0E0E0   #88C0D0   #345995   #1F77B4
fill.mid     #8c8c8c   #4DAF4A   #4DAF4A   #BDBDBD   #A3BE8C   #4B7355   #2CA02C
fill.dark    #595959   #E41A1C   #E41A1C   #636363   #BF616A   #8C2F39   #D62728
fill.faint   #d9d9d9   #FF7F00   #FF7F00   #969696   #EBCB8B   #B8621B   #FF7F0E
============ ========= ========= ========= ========= ========= ========= =========

Row sources (all non-manual cells):

- ink ... muted: spec table, which takes them from uv (axis/label, ic, path, budget,
  compensated_budget, eq, ray) and pv (tertiary = shifted, intervention = tax for nord and
  monochrome).
- subtle: uv ``secondary_ic`` = ``ic_color`` at ``secondary_ic_opacity`` 0.45, written as
  the primary colour with alpha ``0x73`` (0.45 x 255 = 114.75, rounded up to 115).
- series.1 / .2 / .3: uv ``sub_effect_color``, ``inc_effect_color``, ``kink_color`` of each
  theme. uv's nord does not set the two effect colours, so it inherits the default orange
  and green; those are kept so utility-viz figures stay identical. monochrome: spec.
- fill.light / .mid / .dark / .faint mean consumer surplus, producer surplus, deadweight
  loss and tax revenue. In the colour themes they follow the curves so the meaning is the
  same in every theme: light = primary (demand), mid = secondary (supply), dark = accent,
  faint = intervention. manual and monochrome keep their explicit grey ladders (spec; pv
  ``MANUAL_COLOR_MODEL`` and ``MONOCHROME_COLOR_MODEL`` cs, ps, dwl, tax_revenue).

Sizes: every theme uses 1.0 for ``line_scale``, ``marker_scale`` and ``label_scale`` except
presentation (1.5, 1.3, 1.25; spec).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from mosaickit.errors import ConfigurationError

ROLES: tuple[str, ...] = (
    "background",
    "ink",
    "primary",
    "secondary",
    "constraint",
    "tertiary",
    "accent",
    "intervention",
    "muted",
    "subtle",
    "series.1",
    "series.2",
    "series.3",
    "fill.light",
    "fill.mid",
    "fill.dark",
    "fill.faint",
)

_HEX = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})")


@dataclass(frozen=True)
class ThemeTokens:
    """The colour of every role in :data:`ROLES` plus size multipliers for one theme."""

    name: str
    colors: Mapping[str, str | None] = field(hash=False)
    line_scale: float = 1.0
    marker_scale: float = 1.0
    label_scale: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ConfigurationError("ThemeTokens requires a non-empty name")
        colors = dict(self.colors)
        missing = [role for role in ROLES if role not in colors]
        unknown = sorted(set(colors) - set(ROLES))
        if missing or unknown:
            problems = []
            if missing:
                problems.append(f"missing roles: {', '.join(missing)}")
            if unknown:
                problems.append(f"unknown roles: {', '.join(unknown)}")
            raise ConfigurationError(f"Theme {self.name!r}: {'; '.join(problems)}")
        for role, value in colors.items():
            if role == "background" and value is None:
                continue
            if not isinstance(value, str) or not _HEX.fullmatch(value):
                raise ConfigurationError(
                    f"Theme {self.name!r}: role {role!r} must be #RRGGBB or #RRGGBBAA, "
                    f"got {value!r}"
                )
        for scale in ("line_scale", "marker_scale", "label_scale"):
            value = getattr(self, scale)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise ConfigurationError(f"Theme {self.name!r}: {scale} must be a positive number")
            object.__setattr__(self, scale, float(value))
        ordered = {role: colors[role] for role in ROLES}
        object.__setattr__(self, "colors", MappingProxyType(ordered))

    def color(self, role: str) -> str | None:
        """The colour of *role* (``None`` only for a transparent background).

        An unknown role raises :class:`ConfigurationError`.
        """
        try:
            return self.colors[role]
        except KeyError:
            raise ConfigurationError(
                f"Unknown theme role: {role!r}. Available: {', '.join(ROLES)}"
            ) from None


def _series_fills(
    series: tuple[str, str, str], fills: tuple[str, str, str, str]
) -> dict[str, str | None]:
    return {
        "series.1": series[0],
        "series.2": series[1],
        "series.3": series[2],
        "fill.light": fills[0],
        "fill.mid": fills[1],
        "fill.dark": fills[2],
        "fill.faint": fills[3],
    }


_SUBTLE_ALPHA = "73"  # 0.45 opacity

_MANUAL = {
    "background": "#ffffff",
    "ink": "#1a1a1a",
    "primary": "#8c8c8c",
    "secondary": "#1a1a1a",
    "constraint": "#222222",
    "tertiary": "#6e6e6e",
    "accent": "#1a1a1a",
    "intervention": "#595959",
    "muted": "#8c8c8c",
    "subtle": "#b8b8b8",
    **_series_fills(
        ("#8c8c8c", "#8c8c8c", "#8c8c8c"),
        ("#b8b8b8", "#8c8c8c", "#595959", "#d9d9d9"),
    ),
}

_COLORBLIND = {
    "background": None,
    "ink": "#222222",
    "primary": "#377EB8",
    "secondary": "#4DAF4A",
    "constraint": "#984EA3",
    "tertiary": "#777777",
    "accent": "#E41A1C",
    "intervention": "#FF7F00",
    "muted": "#999999",
    "subtle": "#377EB8" + _SUBTLE_ALPHA,
    **_series_fills(
        ("#FF7F00", "#4DAF4A", "#A65628"),
        ("#377EB8", "#4DAF4A", "#E41A1C", "#FF7F00"),
    ),
}

_MONOCHROME = {
    "background": None,
    "ink": "#000000",
    "primary": "#000000",
    "secondary": "#000000",
    "constraint": "#000000",
    "tertiary": "#6E6E6E",
    "accent": "#000000",
    "intervention": "#2E2E2E",
    "muted": "#555555",
    "subtle": "#000000" + _SUBTLE_ALPHA,
    **_series_fills(
        ("#000000", "#000000", "#000000"),
        ("#E0E0E0", "#BDBDBD", "#636363", "#969696"),
    ),
}

_NORD = {
    "background": None,
    "ink": "#2E3440",
    "primary": "#88C0D0",
    "secondary": "#A3BE8C",
    "constraint": "#5E81AC",
    "tertiary": "#4C566A",
    "accent": "#BF616A",
    "intervention": "#EBCB8B",
    "muted": "#4C566A",
    "subtle": "#88C0D0" + _SUBTLE_ALPHA,
    **_series_fills(
        ("#FF7F00", "#4DAF4A", "#88C0D0"),
        ("#88C0D0", "#A3BE8C", "#BF616A", "#EBCB8B"),
    ),
}

_PAPER = {
    "background": None,
    "ink": "#1A1A1A",
    "primary": "#345995",
    "secondary": "#4B7355",
    "constraint": "#5C5C5C",
    "tertiary": "#8C8C8C",
    "accent": "#8C2F39",
    "intervention": "#B8621B",
    "muted": "#8C8C8C",
    "subtle": "#345995" + _SUBTLE_ALPHA,
    **_series_fills(
        ("#B8621B", "#4B7355", "#6B4226"),
        ("#345995", "#4B7355", "#8C2F39", "#B8621B"),
    ),
}

_PRESENTATION = {
    "background": None,
    "ink": "#1A1A1A",
    "primary": "#1F77B4",
    "secondary": "#2CA02C",
    "constraint": "#9467BD",
    "tertiary": "#7F7F7F",
    "accent": "#D62728",
    "intervention": "#FF7F0E",
    "muted": "#7F7F7F",
    "subtle": "#1F77B4" + _SUBTLE_ALPHA,
    **_series_fills(
        ("#FF7F0E", "#2CA02C", "#8C564B"),
        ("#1F77B4", "#2CA02C", "#D62728", "#FF7F0E"),
    ),
}

SHARED_THEMES: Mapping[str, ThemeTokens] = MappingProxyType(
    {
        tokens.name: tokens
        for tokens in (
            ThemeTokens("manual", _MANUAL),
            ThemeTokens("default", _COLORBLIND),
            ThemeTokens("colorblind", _COLORBLIND),
            ThemeTokens("monochrome", _MONOCHROME),
            ThemeTokens("nord", _NORD),
            ThemeTokens("paper", _PAPER),
            ThemeTokens(
                "presentation", _PRESENTATION, line_scale=1.5, marker_scale=1.3, label_scale=1.25
            ),
        )
    }
)


def list_shared_themes() -> tuple[str, ...]:
    """The names of the shared themes, in definition order."""
    return tuple(SHARED_THEMES)


def get_tokens(name: str) -> ThemeTokens:
    """The tokens of the shared theme *name* (case and surrounding spaces ignored)."""
    key = name.strip().lower() if isinstance(name, str) else name
    try:
        return SHARED_THEMES[key]
    except (KeyError, TypeError):
        raise ConfigurationError(
            f"Unknown shared theme: {name!r}. Available: {', '.join(list_shared_themes())}"
        ) from None


__all__ = ["ROLES", "SHARED_THEMES", "ThemeTokens", "get_tokens", "list_shared_themes"]
