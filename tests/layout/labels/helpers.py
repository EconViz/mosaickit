"""Checks shared by the label tests: the hard requirements as functions."""

from __future__ import annotations

import math
from collections.abc import Sequence

from mosaickit.layout import Rect
from mosaickit.layout.geometry import rect_hits_segment
from mosaickit.layout.labels import Label, LabelOptions, Obstacle, PlacementResult


def reach(options: LabelOptions) -> float:
    """The furthest an offset can be from its anchor under ``options``."""
    return math.sqrt(2) * (options.gap + options.rings * options.ring_step) + 1e-6


def violations(
    result: PlacementResult,
    labels: Sequence[Label],
    obstacles: Sequence[Obstacle],
    bounds: Rect,
    options: LabelOptions,
) -> list[str]:
    """Every broken requirement among the placements that claim to be fine."""
    problems: list[str] = []
    placed = {p.label_id: p for p in result.placements if p.ok}
    for label in labels:
        p = placed.get(label.id)
        if p is None:
            continue
        box = p.box
        if not box.within(bounds):
            problems.append(f"{label.id}: outside bounds")
        if not (
            math.isclose(box.width, label.size[0], abs_tol=1e-6)
            and math.isclose(box.height, label.size[1], abs_tol=1e-6)
        ):
            problems.append(f"{label.id}: size changed")
        if math.dist(box.nearest_point(label.anchor), label.anchor) > reach(options):
            problems.append(f"{label.id}: not next to its own anchor")
        for obstacle in obstacles:
            pad = options.own_clearance if obstacle.owner == label.owner_key else options.clearance
            probe = box.inflate(pad - 1e-6)
            if obstacle.box is not None and probe.intersects(obstacle.box):
                problems.append(f"{label.id}: overlaps a box")
            if any(rect_hits_segment(probe, a, b) for a, b in obstacle.segments):
                problems.append(f"{label.id}: touches a line")
        for other in labels:
            if other.id != label.id and box.inflate(options.anchor_clearance - 1e-6).contains(
                other.anchor
            ):
                problems.append(f"{label.id}: covers the anchor of {other.id}")
    ids = list(placed)
    for i, first in enumerate(ids):
        for second in ids[i + 1 :]:
            if placed[first].box.inflate(options.label_gap - 1e-6).intersects(placed[second].box):
                problems.append(f"{first} overlaps {second}")
    return problems
