"""Callout leaders: build one, and count what it would cover.

A leader starts inside its own region and leaves it once. Past that exit it may
not cross any line, point, text, or other region.
"""

import math

import numpy as np

from mosaickit.layout.geometry import (
    Point,
    Rect,
    Segment,
    point_in_polygon,
    polygon_edges,
    ray_exit,
    rect_hits_segment,
    segments_intersect,
)
from mosaickit.layout.geometry.arrays import (
    SMALL,
    point_in_edges,
    polygon_array,
    segment_array,
    segments_intersect_many,
)
from mosaickit.layout.placement.obstacles import Obstacles

_ON_BOUNDARY = 1.5  # px past the exit, so touching the region's own edge is not a crossing


def build_leader(pole: Point, rect: Rect, gap: float) -> Segment:
    """From ``pole`` to the nearest point of ``rect``, stopping ``gap`` short."""
    end = rect.nearest_point(pole)
    length = math.dist(pole, end)
    if length <= gap:
        return (pole, end)
    ratio = (length - gap) / length
    return (pole, (pole[0] + (end[0] - pole[0]) * ratio, pole[1] + (end[1] - pole[1]) * ratio))


def _outside_part(leader: Segment, own: tuple[Point, ...]) -> Segment | None:
    """The part of the leader past where it leaves its own region, or None."""
    (ax, ay), (bx, by) = leader
    length = math.hypot(bx - ax, by - ay)
    if length == 0:
        return None
    direction = ((bx - ax) / length, (by - ay) / length)
    start = ray_exit(leader[0], direction, own) + _ON_BOUNDARY
    if start >= length:
        return None
    return ((ax + direction[0] * start, ay + direction[1] * start), (bx, by))


def leader_violations(leader: Segment, obstacles: Obstacles, own: tuple[Point, ...]) -> int:
    outside = _outside_part(leader, own)
    if outside is None:
        return 0
    a, b = outside
    if len(obstacles.segments) < SMALL and all(len(p) < SMALL for p in obstacles.polygons):
        return _violations_loop(a, b, obstacles, own)
    (ax, ay), (bx, by) = a, b
    count = 0
    if obstacles.segments:
        s = segment_array(obstacles.segments)
        hits = segments_intersect_many(ax, ay, bx, by, s[:, 0], s[:, 1], s[:, 2], s[:, 3])
        count += int(np.count_nonzero(hits))
    count += sum(1 for rect in obstacles.rects if rect_hits_segment(rect, a, b))
    for polygon in obstacles.polygons:
        if polygon == own:
            continue
        e = polygon_array(polygon)
        crossing = segments_intersect_many(ax, ay, bx, by, e[:, 0], e[:, 1], e[:, 2], e[:, 3])
        if point_in_edges(b, e) or bool(np.any(crossing)):
            count += 1
    return count


def _violations_loop(a: Point, b: Point, obstacles: Obstacles, own: tuple[Point, ...]) -> int:
    count = sum(1 for c, d in obstacles.segments if segments_intersect(a, b, c, d))
    count += sum(1 for rect in obstacles.rects if rect_hits_segment(rect, a, b))
    count += sum(
        1
        for polygon in obstacles.polygons
        if polygon != own
        and (
            point_in_polygon(b, polygon)
            or any(segments_intersect(a, b, c, d) for c, d in polygon_edges(polygon))
        )
    )
    return count
