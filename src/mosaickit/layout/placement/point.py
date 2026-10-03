"""Search positions right beside a point for its label.

Principle: cover nothing, stay close. The text sits just outside the point's
footprint (its marker, or the bare point) and may not leave the bounds or touch
any line, rect (other markers, other text), or filled region. Obstacle rects
lying within the footprint are the point's own marker: they set how far out the
search starts instead of blocking it. There is no leader.

Candidates run nearest gap first; within a gap, directions run from upper-right
outwards (ties go counter-clockwise first). The first candidate that covers
nothing wins; if none does, the one with fewest violations wins, earliest first.
"""

from mosaickit.layout.geometry import Point, Rect
from mosaickit.layout.placement.candidates import anchored_rect, direction
from mosaickit.layout.placement.obstacles import Obstacles, Placement, count_violations

DIRECTIONS = 16
GAPS = (4.0, 7.0, 11.0, 16.0)  # pt from the footprint's edge
_PREFERRED = 2  # index of the upper-right direction (45°)


def _order() -> tuple[int, ...]:
    def offset(k: int) -> tuple[int, int]:
        steps = (k - _PREFERRED) % DIRECTIONS
        return (min(steps, DIRECTIONS - steps), 0 if steps <= DIRECTIONS // 2 else 1)

    return tuple(sorted(range(DIRECTIONS), key=offset))


ORDER = _order()


def _edge_distance(footprint: Rect, unit: Point) -> float:
    """Distance from the footprint's centre to its edge along ``unit``."""
    reach = [
        half / abs(component)
        for half, component in ((footprint.width / 2, unit[0]), (footprint.height / 2, unit[1]))
        if abs(component) > 1e-12
    ]
    return min(reach, default=0.0)


def place_point_label(
    footprint: Rect,
    size: tuple[float, float],
    obstacles: Obstacles,
    bounds: Rect,
    *,
    scale: float = 1.0,
) -> Placement:
    """Nearest position for a ``size`` label beside ``footprint``.

    ``scale`` converts the point-based gaps to pixels.
    """
    others = Obstacles(
        obstacles.segments,
        tuple(rect for rect in obstacles.rects if not rect.within(footprint)),
        obstacles.polygons,
    )
    origin = footprint.center
    best: tuple[int, Placement] | None = None
    for gap in GAPS:
        for k in ORDER:
            unit = direction(k, DIRECTIONS)
            rect = anchored_rect(origin, unit, _edge_distance(footprint, unit) + gap * scale, size)
            violations = count_violations(rect, others, bounds, others.polygons) + int(
                rect.intersects(footprint)
            )
            if violations == 0:
                return Placement(rect, None, 0)
            if best is None or violations < best[0]:
                best = (violations, Placement(rect, None, violations))
    assert best is not None
    return best[1]
