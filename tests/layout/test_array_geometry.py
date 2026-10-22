"""The array tests count exactly what the per-segment loops count."""

from __future__ import annotations

import random

import pytest

from mosaickit.layout.geometry import Rect, point_in_polygon, rect_overlaps_polygon
from mosaickit.layout.geometry.arrays import (
    SMALL,
    point_in_edges,
    polygon_array,
    rect_hits_segments,
    segment_array,
    segments_intersect_many,
)
from mosaickit.layout.geometry.segments import rect_hits_segment, segments_intersect
from mosaickit.layout.placement import leader, obstacles
from mosaickit.layout.placement.obstacles import Obstacles

BOUNDS = Rect(0.0, 0.0, 40.0, 40.0)


class Scene:
    """Random obstacles. On even trials all coordinates are integers, so collinear and
    touching cases, where an orientation product is exactly zero, are common."""

    def __init__(self, seed: int = 20261021) -> None:
        self.rng = random.Random(seed)
        self.grid = True

    def coord(self) -> float:
        return float(self.rng.randint(0, 40)) if self.grid else self.rng.uniform(0, 40)

    def point(self):
        return (self.coord(), self.coord())

    def rect(self) -> Rect:
        x0, x1 = sorted((self.coord(), self.coord()))
        y0, y1 = sorted((self.coord(), self.coord()))
        return Rect(x0, y0, x1, y1)

    def polygon(self):
        cx, cy = self.point()
        size = self.rng.choice((3, 5, SMALL + 8))  # below and above the array threshold
        return tuple(
            (
                cx + self.rng.choice((-1, 1)) * self.rng.randint(1, 8),
                cy + self.rng.choice((-1, 1)) * self.rng.randint(1, 8),
            )
            for _ in range(size)
        )

    def obstacles(self, trial: int) -> Obstacles:
        self.grid = trial % 2 == 0
        count = self.rng.choice(
            (self.rng.randint(0, SMALL - 1), self.rng.randint(SMALL, 3 * SMALL))
        )
        return Obstacles(
            tuple((self.point(), self.point()) for _ in range(count)),
            tuple(self.rect() for _ in range(self.rng.randint(0, 3))),
            tuple(self.polygon() for _ in range(self.rng.randint(0, 3))),
        )


def test_count_violations_matches_the_loop() -> None:
    scene = Scene()
    for trial in range(2000):
        obs = scene.obstacles(trial)
        rect = scene.rect()
        assert obstacles.count_violations(rect, obs, BOUNDS, obs.polygons) == (
            obstacles._count_violations_loop(rect, obs, BOUNDS, obs.polygons)
        ), trial


def test_leader_violations_match_the_loop() -> None:
    scene = Scene(7)
    for trial in range(2000):
        obs = scene.obstacles(trial)
        own = obs.polygons[0] if obs.polygons else ((1.0, 1.0), (3.0, 1.0), (2.0, 3.0))
        lead = (scene.point(), scene.point())
        outside = leader._outside_part(lead, own)
        expected = 0 if outside is None else leader._violations_loop(*outside, obs, own)
        assert leader.leader_violations(lead, obs, own) == expected, trial


def test_each_kernel_matches_its_scalar_function() -> None:
    scene = Scene(11)
    for trial in range(400):
        obs = scene.obstacles(trial)
        a, b = scene.point(), scene.point()
        rect = scene.rect()
        if obs.segments:
            array = segment_array(obs.segments)
            hits = segments_intersect_many(
                a[0], a[1], b[0], b[1], array[:, 0], array[:, 1], array[:, 2], array[:, 3]
            )
            assert hits.tolist() == [segments_intersect(a, b, c, d) for c, d in obs.segments]
            assert rect_hits_segments(rect, array).tolist() == [
                rect_hits_segment(rect, c, d) for c, d in obs.segments
            ]
        for polygon in obs.polygons:
            edges = polygon_array(polygon)
            point = scene.point()
            assert point_in_edges(point, edges) == point_in_polygon(point, polygon)
            assert rect_overlaps_polygon(rect, polygon) == obstacles._overlaps(rect, polygon)


def test_a_degenerate_obstacle_set_is_counted_like_the_loop() -> None:
    same_point = tuple(((5.0, 5.0), (5.0, 5.0)) for _ in range(SMALL + 3))
    obs = Obstacles(same_point)
    rect = Rect(4.0, 4.0, 6.0, 6.0)
    assert obstacles.count_violations(rect, obs, BOUNDS, ()) == obstacles._count_violations_loop(
        rect, obs, BOUNDS, ()
    )


@pytest.mark.parametrize("count", [0, 1, SMALL - 1, SMALL])
def test_the_threshold_does_not_change_the_count(count: int) -> None:
    scene = Scene(3)
    segments = tuple((scene.point(), scene.point()) for _ in range(count))
    obs = Obstacles(segments)
    rect = scene.rect()
    assert obstacles.count_violations(rect, obs, BOUNDS, ()) == obstacles._count_violations_loop(
        rect, obs, BOUNDS, ()
    )
