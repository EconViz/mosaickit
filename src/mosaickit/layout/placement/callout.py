"""Search positions around a region for a callout label.

Principle: cover nothing. The text may not touch any line, point, text, or region
(its own included), must sit in open space rather than a small enclosed pocket,
and must stay on the region's side of any crossing the region touches. The leader
may not cross anything after leaving its own region. Among positions that
cover nothing, the shortest leader wins; ties keep the earlier candidate (16
directions from +x counter-clockwise, near gaps first), so results are deterministic.
"""

import math

from mosaickit.layout.geometry import Polygon, Rect, polylabel, ray_exit
from mosaickit.layout.placement.candidates import anchored_rect, direction
from mosaickit.layout.placement.crossings import beyond_crossings, region_crossings
from mosaickit.layout.placement.leader import build_leader, leader_violations
from mosaickit.layout.placement.obstacles import Obstacles, Placement, count_violations
from mosaickit.layout.placement.open_area import open_area

DIRECTIONS = 16
GAPS = (12.0, 24.0, 40.0)
FAR_GAPS = (60.0, 90.0)
LEADER_GAP = 2.0
OPEN_AREA_CELL = 4.0
CROSSING_TOLERANCE = 1.5  # px


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
    everything = Obstacles(obstacles.segments, obstacles.rects, polygons)
    area = open_area(bounds, everything, OPEN_AREA_CELL * scale)
    crossings = region_crossings(own, obstacles.segments, tolerance=CROSSING_TOLERANCE)
    best: tuple[tuple[int, float], Placement] | None = None
    for gaps in (GAPS, FAR_GAPS):
        for k in range(DIRECTIONS):
            unit = direction(k, DIRECTIONS)
            exit_distance = ray_exit(pole, unit, own)
            for gap in gaps:
                rect = anchored_rect(pole, unit, exit_distance + gap * scale, size)
                leader = build_leader(pole, rect, LEADER_GAP * scale)
                violations = (
                    count_violations(rect, obstacles, bounds, polygons)
                    + (0 if area.contains(rect.center) else 1)
                    + leader_violations(leader, everything, own)
                    + beyond_crossings(rect.center, pole, crossings)
                )
                key = (violations, math.dist(*leader))
                if best is None or key < best[0]:
                    best = (key, Placement(rect, leader, violations))
        assert best is not None
        if best[1].violations == 0:
            break
    assert best is not None
    return best[1]
