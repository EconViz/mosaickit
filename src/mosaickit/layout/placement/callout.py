"""Search positions around a region for a callout label.

Candidates: 16 directions from +x counter-clockwise; along each, start where the
ray leaves the region and add a gap. Fewest violations wins, then lowest score;
ties keep the earlier candidate so results are deterministic.
"""

import math

from mosaickit.layout.geometry import (
    Point,
    Polygon,
    Rect,
    Segment,
    polygon_edges,
    polylabel,
    ray_exit,
    segments_intersect,
)
from mosaickit.layout.placement.obstacles import Obstacles, Placement, count_violations

DIRECTIONS = 16
GAPS = (12.0, 24.0, 40.0)
FAR_GAPS = (60.0, 90.0)
LEADER_GAP = 2.0
LINE_PENALTY = 1000.0
REGION_PENALTY = 200.0
_SIDE = 0.38  # |cos| above this anchors the rect by its near side, otherwise by its middle


def _candidate(pole: Point, direction: Point, distance: float, size: tuple[float, float]) -> Rect:
    dx, dy = direction
    cx, cy = pole[0] + dx * distance, pole[1] + dy * distance
    width, height = size
    x0 = cx if dx > _SIDE else cx - width if dx < -_SIDE else cx - width / 2
    y0 = cy if dy > _SIDE else cy - height if dy < -_SIDE else cy - height / 2
    return Rect(x0, y0, x0 + width, y0 + height)


def _leader(pole: Point, rect: Rect, gap: float) -> Segment:
    end = rect.nearest_point(pole)
    length = math.dist(pole, end)
    if length <= gap:
        return (pole, end)
    ratio = (length - gap) / length
    return (pole, (pole[0] + (end[0] - pole[0]) * ratio, pole[1] + (end[1] - pole[1]) * ratio))


def _score(leader: Segment, obstacles: Obstacles, own: tuple[Point, ...]) -> float:
    a, b = leader
    lines = sum(1 for c, d in obstacles.segments if segments_intersect(a, b, c, d))
    regions = sum(
        1
        for polygon in obstacles.polygons
        if polygon != own and any(segments_intersect(a, b, c, d) for c, d in polygon_edges(polygon))
    )
    # The leader starts inside its region, so crossing one boundary line is free.
    return math.dist(a, b) + LINE_PENALTY * max(0, lines - 1) + REGION_PENALTY * regions


def place_callout(
    polygon: Polygon,
    size: tuple[float, float],
    obstacles: Obstacles,
    bounds: Rect,
    *,
    scale: float = 1.0,
) -> Placement:
    """Best callout position. ``scale`` converts the point-based gaps to pixels."""
    own = tuple(polygon)
    pole = polylabel(own)
    # The label may never cover its own region, even when it is not an obstacle.
    polygons = obstacles.polygons if own in obstacles.polygons else (*obstacles.polygons, own)
    best: tuple[tuple[int, float], Placement] | None = None
    for gaps in (GAPS, FAR_GAPS):
        for k in range(DIRECTIONS):
            angle = 2 * math.pi * k / DIRECTIONS
            direction = (math.cos(angle), math.sin(angle))
            exit_distance = ray_exit(pole, direction, own)
            for gap in gaps:
                rect = _candidate(pole, direction, exit_distance + gap * scale, size)
                leader = _leader(pole, rect, LEADER_GAP * scale)
                key = (
                    count_violations(rect, obstacles, bounds, polygons),
                    _score(leader, obstacles, own),
                )
                if best is None or key < best[0]:
                    best = (key, Placement(rect, leader, key[0]))
        assert best is not None
        if best[1].violations == 0:
            break
    assert best is not None
    return best[1]
