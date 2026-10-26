"""Property-style tests: the hard requirements hold on many seeded random figures."""

from __future__ import annotations

import random
from functools import cache

import pytest
from helpers import violations
from scenes import CANVAS

from mosaickit.layout.labels import Label, LabelOptions, Obstacle, PlacementResult, place_labels

SEEDS = range(30)


def random_figure(seed: int) -> tuple[list[Label], list[Obstacle]]:
    rng = random.Random(seed)
    labels: list[Label] = []
    obstacles: list[Obstacle] = []
    for i in range(rng.randint(2, 6)):
        x, y = rng.uniform(10, 120), rng.uniform(10, 120)
        points = [(x, y)]
        for _ in range(rng.randint(2, 40)):
            x += rng.uniform(2, 9)
            y += rng.uniform(-4, 8)
            points.append((min(x, 340.0), min(max(y, 5.0), 270.0)))
        owner = f"c{i}"
        obstacles.append(Obstacle.polyline(points, owner=owner))
        size = (rng.uniform(15, 80), rng.uniform(10, 40))
        labels.append(Label(owner, points[-1], size, owner=owner))
    for j in range(rng.randint(0, 4)):
        obstacles.append(Obstacle.dot((rng.uniform(0, 360), rng.uniform(0, 280)), 4.0))
        labels.append(
            Label(
                f"pt{j}", (rng.uniform(20, 340), rng.uniform(20, 260)), (rng.uniform(10, 30), 14.0)
            )
        )
    base = rng.uniform(40, 90)
    obstacles.append(Obstacle.polyline([(0.0, base), (360.0, base)], owner="axis"))
    for k in range(rng.randint(0, 6)):
        labels.append(
            Label(
                f"t{k}",
                (rng.uniform(20, 340), base),
                (rng.uniform(10, 40), 14.0),
                sides=("below", "above"),
                spread="stack",
                owner="axis",
            )
        )
    return labels, obstacles


@cache
def solved(seed: int) -> tuple[list[Label], list[Obstacle], PlacementResult]:
    labels, obstacles = random_figure(seed)
    return labels, obstacles, place_labels(labels, obstacles, CANVAS)


@pytest.mark.parametrize("seed", SEEDS)
def test_every_claimed_placement_meets_the_hard_requirements(seed: int) -> None:
    labels, obstacles, result = solved(seed)
    assert violations(result, labels, obstacles, CANVAS, LabelOptions()) == []
    assert [p.label_id for p in result.placements] == [label.id for label in labels]
    failed = {p.label_id for p in result.placements if not p.ok}
    assert failed == {w.label_id for w in result.warnings}


@pytest.mark.parametrize("seed", SEEDS)
def test_size_is_never_changed(seed: int) -> None:
    labels, _, result = solved(seed)
    for label, placed in zip(labels, result.placements, strict=True):
        assert placed.box.width == pytest.approx(label.size[0])
        assert placed.box.height == pytest.approx(label.size[1])


@pytest.mark.parametrize("seed", SEEDS[:10])
def test_same_input_gives_same_output(seed: int) -> None:
    labels, obstacles, first = solved(seed)
    assert place_labels(labels, obstacles, CANVAS) == first


@pytest.mark.parametrize("seed", SEEDS)
def test_offset_and_anchor_agree(seed: int) -> None:
    labels, _, result = solved(seed)
    for label, placed in zip(labels, result.placements, strict=True):
        if not placed.ok:
            continue
        # the box edge named by the text anchor sits exactly at anchor + offset
        px, py = label.anchor[0] + placed.offset[0], label.anchor[1] + placed.offset[1]
        assert placed.box.inflate(1e-6).contains((px, py))


def test_a_tiny_search_budget_still_returns_a_valid_answer() -> None:
    labels, obstacles = random_figure(3)
    options = LabelOptions(search_budget=1)
    result = place_labels(labels, obstacles, CANVAS, options)
    assert violations(result, labels, obstacles, CANVAS, options) == []


def test_larger_clearance_is_respected() -> None:
    labels, obstacles = random_figure(7)
    options = LabelOptions(clearance=9.0, label_gap=6.0)
    result = place_labels(labels, obstacles, CANVAS, options)
    assert violations(result, labels, obstacles, CANVAS, options) == []
