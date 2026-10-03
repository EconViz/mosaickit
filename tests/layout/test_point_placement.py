import math

import pytest

from mosaickit.layout import Obstacles, Rect, place_point_label
from mosaickit.layout.geometry import rect_hits_segment

BOUNDS = Rect(0, 0, 300, 300)
DOT = Rect(147, 147, 153, 153)  # a 6 px marker centred on (150, 150)
SIZE = (40, 12)
FIRST_GAP = 4.0  # pt; scale 1 makes it px


def _gap(rect: Rect, footprint: Rect) -> float:
    """Clearance between the label and the marker's edge, along the label direction."""
    nearest = rect.nearest_point(footprint.center)
    return math.dist(footprint.nearest_point(nearest), nearest)


def test_open_space_puts_the_label_up_and_right_at_the_first_gap():
    placement = place_point_label(DOT, SIZE, Obstacles(), BOUNDS)
    assert placement.violations == 0
    assert placement.leader is None
    rect = placement.rect
    assert rect.x0 > DOT.x1 and rect.y0 > DOT.y1
    assert rect.x0 - DOT.center[0] == pytest.approx(rect.y0 - DOT.center[1])
    assert _gap(rect, DOT) == pytest.approx(FIRST_GAP, abs=1.5)


def test_label_never_touches_two_lines_crossing_at_the_point():
    line_a = ((50.0, 50.0), (250.0, 250.0))
    line_b = ((50.0, 250.0), (250.0, 50.0))
    obstacles = Obstacles(segments=(line_a, line_b), rects=(DOT,))
    placement = place_point_label(DOT, SIZE, obstacles, BOUNDS)
    assert placement.violations == 0
    for line in (line_a, line_b):
        assert not rect_hits_segment(placement.rect, *line)
    assert not placement.rect.intersects(DOT)


def test_label_avoids_lines_running_in_its_preferred_direction():
    # Shallow lines through the point leave no room up-right or right at the first gap.
    line_a = ((0.0, 120.0), (300.0, 180.0))
    line_b = ((0.0, 180.0), (300.0, 120.0))
    placement = place_point_label(DOT, SIZE, Obstacles(segments=(line_a, line_b)), BOUNDS)
    assert placement.violations == 0
    for line in (line_a, line_b):
        assert not rect_hits_segment(placement.rect, *line)
    assert placement.rect.y0 > DOT.y1  # above, between the lines


def test_own_marker_is_not_an_obstacle_but_is_never_covered():
    placement = place_point_label(DOT, SIZE, Obstacles(rects=(DOT,)), BOUNDS)
    assert placement.violations == 0
    assert not placement.rect.intersects(DOT)


def test_a_bare_point_is_never_covered():
    point = Rect(150, 150, 150, 150)
    placement = place_point_label(point, SIZE, Obstacles(), BOUNDS)
    assert placement.violations == 0
    assert not placement.rect.contains((150, 150))


def test_other_text_is_avoided_at_the_same_distance():
    taken = place_point_label(DOT, SIZE, Obstacles(), BOUNDS).rect
    placement = place_point_label(DOT, SIZE, Obstacles(rects=(taken,)), BOUNDS)
    assert placement.violations == 0
    assert not placement.rect.intersects(taken)
    assert _gap(placement.rect, DOT) == pytest.approx(FIRST_GAP, abs=1.5)


def test_label_stays_inside_the_bounds():
    corner = Rect(290, 290, 296, 296)
    placement = place_point_label(corner, SIZE, Obstacles(), BOUNDS)
    assert placement.violations == 0
    assert placement.rect.within(BOUNDS)
    assert placement.rect.x1 < corner.x0 or placement.rect.y1 < corner.y0


def test_filled_regions_are_avoided():
    region = ((150.0, 160.0), (300.0, 160.0), (300.0, 300.0), (150.0, 300.0))
    placement = place_point_label(DOT, SIZE, Obstacles(polygons=(region,)), BOUNDS)
    assert placement.violations == 0
    assert placement.rect.y1 < 160 or placement.rect.x1 < 150


def test_scale_converts_gaps_to_pixels():
    placement = place_point_label(DOT, SIZE, Obstacles(), BOUNDS, scale=2.0)
    assert _gap(placement.rect, DOT) == pytest.approx(2 * FIRST_GAP, abs=3)


def test_crowded_point_reports_violations():
    lines = tuple(((0.0, float(y)), (300.0, float(y))) for y in range(0, 301, 5))
    placement = place_point_label(DOT, SIZE, Obstacles(segments=lines), BOUNDS)
    assert placement.violations > 0


def test_point_placement_is_deterministic():
    obstacles = Obstacles(segments=(((0.0, 120.0), (300.0, 180.0)),))
    first = place_point_label(DOT, SIZE, obstacles, BOUNDS)
    assert all(place_point_label(DOT, SIZE, obstacles, BOUNDS) == first for _ in range(3))
