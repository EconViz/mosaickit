"""A figure script places its labels in well under a second."""

from __future__ import annotations

import random
import time

from helpers import violations
from scenes import CANVAS, lm_lines

from mosaickit.layout.labels import Label, LabelOptions, Obstacle, place_labels

LIMIT = 1.5  # seconds; the measured time is about 0.6 s, the slack covers a slow CI machine


def thirty_labels() -> tuple[list[Label], list[Obstacle]]:
    rng = random.Random(5)
    labels: list[Label] = []
    obstacles: list[Obstacle] = []
    for i in range(12):
        x, y = rng.uniform(10, 100), rng.uniform(10, 200)
        pts = [(x, y)]
        for _ in range(60):
            x += rng.uniform(2, 5)
            y += rng.uniform(-2, 4)
            pts.append((min(x, 340.0), min(max(y, 5.0), 270.0)))
        obstacles.append(Obstacle.polyline(pts, owner=f"c{i}"))
        labels.append(Label(f"c{i}", pts[-1], (40.0, 16.0), owner=f"c{i}"))
    for j in range(8):
        anchor = (rng.uniform(20, 340), rng.uniform(20, 260))
        labels.append(Label(f"p{j}", anchor, (24.0, 14.0)))
        obstacles.append(Obstacle.dot(anchor, 4.0))
    obstacles.append(Obstacle.polyline([(0.0, 50.0), (360.0, 50.0)]))
    for k in range(10):
        labels.append(
            Label(
                f"t{k}",
                (20.0 + 33 * k, 50.0),
                (22.0, 14.0),
                sides=("below", "above"),
                spread="stack",
            )
        )
    return labels, obstacles


def test_three_lm_lines_are_instant() -> None:
    labels, obstacles = lm_lines()
    start = time.perf_counter()
    place_labels(labels, obstacles, CANVAS)
    assert time.perf_counter() - start < 0.25


def test_thirty_labels_finish_within_the_limit_and_stay_valid() -> None:
    labels, obstacles = thirty_labels()
    start = time.perf_counter()
    result = place_labels(labels, obstacles, CANVAS)
    assert time.perf_counter() - start < LIMIT
    assert violations(result, labels, obstacles, CANVAS, LabelOptions()) == []
