"""Hard constraints that depend on the label alone, checked once per candidate."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from mosaickit.layout.geometry import Point, Rect, Segment, rect_hits_segment, segments_intersect
from mosaickit.layout.geometry.arrays import (
    SMALL,
    rect_hits_segments,
    segment_array,
    segments_intersect_many,
)
from mosaickit.layout.labels.candidates import Candidate, base_cost, candidates_for
from mosaickit.layout.labels.model import Label, Obstacle
from mosaickit.layout.labels.options import LabelOptions


@dataclass(frozen=True, slots=True)
class Option:
    """A candidate that passed the unary tests, with its leader and total own cost."""

    candidate: Candidate
    leader: Segment | None
    cost: float

    @property
    def box(self) -> Rect:
        return self.candidate.box


@dataclass(frozen=True, slots=True)
class _Scene:
    """Obstacle geometry split by whether a given label owns it."""

    segments: tuple[Segment, ...]
    boxes: tuple[Rect, ...]


def _split(obstacles: Sequence[Obstacle], owner: str) -> tuple[_Scene, _Scene]:
    own_s: list[Segment] = []
    own_b: list[Rect] = []
    other_s: list[Segment] = []
    other_b: list[Rect] = []
    for obstacle in obstacles:
        mine = obstacle.owner == owner
        (own_s if mine else other_s).extend(obstacle.segments)
        if obstacle.box is not None:
            (own_b if mine else other_b).append(obstacle.box)
    return _Scene(tuple(own_s), tuple(own_b)), _Scene(tuple(other_s), tuple(other_b))


def _hits_segments(rect: Rect, segments: tuple[Segment, ...], array: np.ndarray | None) -> bool:
    if array is not None:
        return bool(np.any(rect_hits_segments(rect, array)))
    return any(rect_hits_segment(rect, a, b) for a, b in segments)


def _blocked(rect: Rect, scene: _Scene, array: np.ndarray | None, pad: float) -> bool:
    probe = rect.inflate(pad)
    return any(probe.intersects(box) for box in scene.boxes) or _hits_segments(
        probe, scene.segments, array
    )


def _owned_by(label: Label, box: Rect, foreign: Sequence[Point], options: LabelOptions) -> bool:
    """Whether the box is nearer its own anchor than any other label's, by ``ownership_margin``,
    so it cannot be read as belonging to a neighbour. A leader or a tick row states ownership
    on its own and skips this test."""
    own = math.dist(box.nearest_point(label.anchor), label.anchor)
    return all(
        own + options.ownership_margin <= math.dist(box.nearest_point(p), p) for p in foreign
    )


def leader_for(label: Label, candidate: Candidate, options: LabelOptions) -> Segment | None:
    """The line from the anchor towards the box, ending ``leader_gap`` short of it."""
    if not candidate.leader_needed:
        return None
    end = candidate.box.nearest_point(label.anchor)
    length = math.dist(label.anchor, end)
    if length <= options.leader_gap:
        return None
    ratio = (length - options.leader_gap) / length
    stop = (
        label.anchor[0] + (end[0] - label.anchor[0]) * ratio,
        label.anchor[1] + (end[1] - label.anchor[1]) * ratio,
    )
    return (label.anchor, stop)


def _crossings(leader: Segment, scene: _Scene, array: np.ndarray | None) -> int:
    a, b = leader
    if array is not None:
        hits = segments_intersect_many(
            a[0], a[1], b[0], b[1], array[:, 0], array[:, 1], array[:, 2], array[:, 3]
        )
        count = int(np.count_nonzero(hits))
    else:
        count = sum(1 for c, d in scene.segments if segments_intersect(a, b, c, d))
    return count + sum(1 for box in scene.boxes if rect_hits_segment(box, a, b))


def feasible_options(
    label: Label,
    obstacles: Sequence[Obstacle],
    foreign_anchors: Sequence[Point],
    bounds: Rect,
    options: LabelOptions,
) -> tuple[list[Option], list[Candidate]]:
    """The candidates of ``label`` that are free, cheapest first, and all candidates.

    Free means: inside ``bounds`` (less ``bounds_margin``), clear of every obstacle by
    ``clearance`` (``own_clearance`` for the label's own), and not covering another label's
    anchor. A leader's crossings with lines add ``leader_crossing_weight`` each.
    """
    own, other = _split(obstacles, label.owner_key)
    other_array = segment_array(other.segments) if len(other.segments) >= SMALL else None
    own_array = segment_array(own.segments) if len(own.segments) >= SMALL else None
    inner = Rect(
        bounds.x0 + options.bounds_margin,
        bounds.y0 + options.bounds_margin,
        bounds.x1 - options.bounds_margin,
        bounds.y1 - options.bounds_margin,
    )
    everything = candidates_for(label, options)
    free: list[tuple[float, int, Option]] = []
    for index, candidate in enumerate(everything):
        box = candidate.box
        if not box.within(inner):
            continue
        if _blocked(box, other, other_array, options.clearance):
            continue
        if _blocked(box, own, own_array, options.own_clearance):
            continue
        probe = box.inflate(options.anchor_clearance)
        if any(probe.contains(point) for point in foreign_anchors):
            continue
        if (
            label.spread == "ring"
            and not candidate.leader_needed
            and not _owned_by(label, box, foreign_anchors, options)
        ):
            continue
        leader = leader_for(label, candidate, options)
        cost = base_cost(candidate, options)
        if leader is not None:
            crossing = _crossings(leader, other, other_array)
            cost += options.leader_weight + options.leader_crossing_weight * crossing
        free.append((cost, index, Option(candidate, leader, cost)))
    free.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in free[: options.domain_limit]], everything
