"""Place every label of a figure at once: ``place_labels``."""

from __future__ import annotations

from collections.abc import Sequence

from mosaickit.layout.geometry import Rect
from mosaickit.layout.labels.candidates import Candidate
from mosaickit.layout.labels.feasibility import Option, feasible_options
from mosaickit.layout.labels.model import (
    Label,
    Obstacle,
    Placement,
    PlacementResult,
    PlacementWarning,
)
from mosaickit.layout.labels.options import LabelOptions
from mosaickit.layout.labels.solver import solve


def _fallback(label: Label, candidates: Sequence[Candidate], bounds: Rect) -> Placement:
    """The preferred position, slid back inside ``bounds`` where it can be, for a label with
    no free spot. It is a marker for the caller, not a clean placement: ``ok`` is False."""
    first = candidates[0]
    box = first.box
    dx = max(bounds.x0 - box.x0, 0.0) + min(bounds.x1 - box.x1, 0.0)
    dy = max(bounds.y0 - box.y0, 0.0) + min(bounds.y1 - box.y1, 0.0)
    offset = (first.offset[0] + dx, first.offset[1] + dy)
    return Placement(
        label.id,
        box.shifted(dx, dy),
        first.side,
        offset,
        None,
        float("inf"),
        False,
        first.text_anchor,
    )


def _placement(label: Label, option: Option) -> Placement:
    c = option.candidate
    return Placement(
        label.id, c.box, c.side, c.offset, option.leader, option.cost, True, c.text_anchor
    )


def place_labels(
    labels: Sequence[Label],
    obstacles: Sequence[Obstacle],
    bounds: Rect,
    options: LabelOptions | None = None,
) -> PlacementResult:
    """Place all ``labels`` together, each next to its own anchor.

    Every box keeps the label's size, lies inside ``bounds``, keeps ``options.clearance`` from
    every obstacle and ``label_gap`` from every other box, and sits at most ``rings`` rings from
    its anchor (with a leader once it is further than ``leader_after``). The result lists the
    placements in input order. A label that cannot be placed free gets ``ok=False`` and a
    fallback box, and a :class:`PlacementWarning` says why; nothing is silently overlapped.
    Label ids must be unique.
    """
    o = options or LabelOptions()
    ids = [label.id for label in labels]
    if len(set(ids)) != len(ids):
        raise ValueError("label ids must be unique")
    domains: list[list[Option]] = []
    everything: list[list[Candidate]] = []
    for index, label in enumerate(labels):
        foreign = [other.anchor for j, other in enumerate(labels) if j != index]
        free, allc = feasible_options(label, obstacles, foreign, bounds, o)
        domains.append(free)
        everything.append(allc)
    solution = solve(domains, o)
    placements: list[Placement] = []
    warnings: list[PlacementWarning] = []
    for index, label in enumerate(labels):
        pick = solution.chosen[index]
        if pick is not None:
            placements.append(_placement(label, domains[index][pick]))
            continue
        placements.append(_fallback(label, everything[index], bounds))
        if not domains[index]:
            warnings.append(PlacementWarning(label.id, "no-free-position"))
        elif solution.exhausted:
            warnings.append(PlacementWarning(label.id, "search-budget"))
        else:
            warnings.append(PlacementWarning(label.id, "conflict"))
    return PlacementResult(tuple(placements), tuple(warnings))
