import pytest

from mosaickit.layout import Obstacles, Rect, fits_inside, place_callout
from mosaickit.layout.geometry import rect_hits_segment, rect_overlaps_polygon

BOUNDS = Rect(0, 0, 300, 300)
BIG = ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0))
SMALL = ((100.0, 100.0), (110.0, 100.0), (110.0, 110.0), (100.0, 110.0))


def test_fits_inside_centres_on_the_pole():
    rect = fits_inside(BIG, (20, 10), Obstacles(polygons=(BIG,)), BOUNDS)
    assert rect == Rect(40, 45, 60, 55)


def test_fits_inside_rejects_oversized_text():
    assert fits_inside(SMALL, (40, 12), Obstacles(polygons=(SMALL,)), BOUNDS) is None


def test_fits_inside_rejects_a_line_through_the_text():
    line = Obstacles(segments=(((0.0, 50.0), (100.0, 50.0)),), polygons=(BIG,))
    assert fits_inside(BIG, (20, 10), line, BOUNDS) is None


def test_callout_without_obstacles_goes_right_at_the_first_gap():
    placement = place_callout(SMALL, (40, 12), Obstacles(polygons=(SMALL,)), BOUNDS)
    assert placement.violations == 0
    assert placement.rect.x0 == pytest.approx(110 + 12)
    assert placement.leader[0] == pytest.approx((105, 105), abs=0.5)
    assert not rect_overlaps_polygon(placement.rect, SMALL)


def test_callout_never_covers_its_own_region_even_when_not_an_obstacle():
    placement = place_callout(SMALL, (40, 12), Obstacles(), BOUNDS)
    assert not rect_overlaps_polygon(placement.rect, SMALL)


def test_callout_avoids_a_blocking_line():
    wall = ((125.0, 0.0), (125.0, 300.0))
    obstacles = Obstacles(segments=(wall,), polygons=(SMALL,))
    placement = place_callout(SMALL, (40, 12), obstacles, BOUNDS)
    assert placement.violations == 0
    assert not rect_hits_segment(placement.rect, *wall)


def test_callout_is_deterministic():
    obstacles = Obstacles(segments=(((125.0, 0.0), (125.0, 300.0)),), polygons=(SMALL,))
    first = place_callout(SMALL, (40, 12), obstacles, BOUNDS)
    assert all(place_callout(SMALL, (40, 12), obstacles, BOUNDS) == first for _ in range(3))


def test_callout_reports_violations_when_everything_is_blocked():
    lines = tuple(((0.0, float(y)), (300.0, float(y))) for y in range(0, 301, 5))
    obstacles = Obstacles(segments=lines, polygons=(SMALL,))
    assert place_callout(SMALL, (40, 12), obstacles, BOUNDS).violations > 0


def test_obstacles_extended_keeps_polygons():
    base = Obstacles(polygons=(SMALL,))
    grown = base.extended(segments=(((0.0, 0.0), (1.0, 1.0)),), rects=(Rect(0, 0, 1, 1),))
    assert grown.polygons == (SMALL,)
    assert len(grown.segments) == 1 and len(grown.rects) == 1
