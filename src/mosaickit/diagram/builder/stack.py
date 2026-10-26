"""Stacking panels into a grid, with links between their named points."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from mosaickit.canvas import CanvasGrid, GridLink, GridSpacing
from mosaickit.diagram.builder.diagram import Diagram
from mosaickit.errors import ConfigurationError
from mosaickit.styles import Stroke


@dataclass(frozen=True, slots=True)
class PointLink:
    """A link between named points of two panels of a :func:`stack`."""

    start_panel: int
    start: str
    end_panel: int
    end: str
    role: str = "link"
    stroke: Stroke | None = None


def link_points(
    upper: int,
    lower: int,
    names: Iterable[str],
    *,
    role: str = "link",
    stroke: Stroke | None = None,
) -> list[PointLink]:
    """One :class:`PointLink` per name, joining the point of that name in panel ``upper`` to
    the same-named point in panel ``lower`` (panels numbered in stacking order)."""
    return [PointLink(upper, n, lower, n, role=role, stroke=stroke) for n in names]


def stack(
    panels: Sequence[Diagram],
    links: Iterable[PointLink] = (),
    *,
    cols: int = 1,
    spacing: GridSpacing | None = None,
) -> CanvasGrid:
    """Panels in a :class:`~mosaickit.CanvasGrid` (one column by default, row by row), with
    each :class:`PointLink` resolved to a :class:`~mosaickit.GridLink` between their points."""
    if not panels:
        raise ConfigurationError("stack() needs at least one panel")
    resolved = []
    for link in links:
        for index in (link.start_panel, link.end_panel):
            if not 0 <= index < len(panels):
                raise ConfigurationError(f"link panel {index} is not one of {len(panels)} panels")
        resolved.append(
            GridLink(
                link.start_panel,
                panels[link.start_panel].at(link.start),
                link.end_panel,
                panels[link.end_panel].at(link.end),
                role=link.role,
                stroke=link.stroke,
            )
        )
    return CanvasGrid(
        [panel.canvas() for panel in panels], cols=cols, links=resolved, spacing=spacing
    )
