import pytest

from mosaickit.layout import Obstacles, Rect
from mosaickit.layout.placement import place_beside

BOUNDS = Rect(0, 0, 400, 400)


def test_label_sits_just_past_the_tip_when_space_is_free():
    rect, violations = place_beside(
        (100, 200), (40, 20), axis="y", direction=1, reach=50, obstacles=Obstacles(), bounds=BOUNDS
    )
    assert violations == 0
    assert rect.x0 > 100 and rect.x0 - 100 < 6
    assert rect.center[1] == pytest.approx(200)


def test_label_points_the_other_way_for_negative_direction():
    rect, _ = place_beside(
        (100, 200), (40, 20), axis="y", direction=-1, reach=0, obstacles=Obstacles(), bounds=BOUNDS
    )
    assert rect.x1 < 100


def test_label_slides_along_the_span_to_avoid_a_line():
    line = ((0.0, 200.0), (400.0, 200.0))
    rect, violations = place_beside(
        (100, 200),
        (40, 20),
        axis="y",
        direction=1,
        reach=50,
        obstacles=Obstacles(segments=(line,)),
        bounds=BOUNDS,
    )
    assert violations == 0
    assert not (rect.y0 <= 200 <= rect.y1)
    assert abs(rect.center[1] - 200) <= 50


def test_label_moves_further_out_when_the_whole_span_is_blocked():
    blocker = Rect(100, 100, 130, 300)
    rect, violations = place_beside(
        (100, 200),
        (40, 20),
        axis="y",
        direction=1,
        reach=30,
        obstacles=Obstacles(rects=(blocker,)),
        bounds=BOUNDS,
    )
    assert violations == 0
    assert rect.x0 > 130


def test_horizontal_axis_places_the_label_across_y():
    rect, violations = place_beside(
        (200, 100), (40, 20), axis="x", direction=1, reach=0, obstacles=Obstacles(), bounds=BOUNDS
    )
    assert violations == 0
    assert rect.y0 > 100
    assert rect.center[0] == pytest.approx(200)


def test_reports_violations_when_nothing_is_free():
    rect, violations = place_beside(
        (100, 200),
        (40, 20),
        axis="y",
        direction=1,
        reach=10,
        obstacles=Obstacles(rects=(Rect(0, 0, 400, 400),)),
        bounds=BOUNDS,
    )
    assert violations > 0
    assert isinstance(rect, Rect)
