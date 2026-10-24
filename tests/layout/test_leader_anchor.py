import math

import pytest

from mosaickit.layout import Obstacles, Rect, follow_leader, leader_anchor, place_callout
from mosaickit.layout.geometry import rect_hits_segment
from mosaickit.layout.placement.leader import build_leader

BOX = Rect(100, 200, 160, 220)  # 60 x 20, centre (130, 210)
CX, CY = BOX.center
W2, H2 = BOX.width / 2, BOX.height / 2

# anchor number -> (sx, sy), drawn with y up:  1 2 3 / 4 . 5 / 6 7 8
STEPS = {
    1: (-1, 1),
    2: (0, 1),
    3: (1, 1),
    4: (-1, 0),
    5: (1, 0),
    6: (-1, -1),
    7: (0, -1),
    8: (1, -1),
}


def anchor(number):
    sx, sy = STEPS[number]
    return (CX + sx * W2, CY + sy * H2)


def pole_at(degrees, radius=100.0):
    angle = math.radians(degrees)
    return (CX + radius * math.cos(angle), CY + radius * math.sin(angle))


@pytest.mark.parametrize(
    ("degrees", "number"),
    [(0, 5), (45, 3), (90, 2), (135, 1), (180, 4), (225, 6), (270, 7), (315, 8)],
)
def test_each_octant_picks_the_anchor_facing_the_pole(degrees, number):
    assert leader_anchor(pole_at(degrees), BOX) == pytest.approx(anchor(number))


@pytest.mark.parametrize("offset", [-22, -10, 0, 10, 22])
def test_whole_octant_shares_one_anchor(offset):
    for degrees, number in [(0, 5), (45, 3), (90, 2), (135, 1), (180, 4), (225, 6), (270, 7)]:
        assert leader_anchor(pole_at(degrees + offset), BOX) == pytest.approx(anchor(number))


def test_octant_boundaries_take_the_diagonal_step_and_flip_just_past():
    box = Rect(-30, -10, 30, 10)
    t = math.tan(math.pi / 8)
    # exactly on a 22.5 degree line the minor axis is already stepped: a corner, not a mid-edge
    assert leader_anchor((100.0, 100.0 * t), box) == (30, 10)
    assert leader_anchor((100.0, 100.0 * t * 0.999), box) == (30, 0)
    assert leader_anchor((100.0 * t, 100.0), box) == (30, 10)
    assert leader_anchor((100.0 * t * 0.999, 100.0), box) == (0, 10)
    assert leader_anchor((-100.0, -100.0 * t), box) == (-30, -10)
    assert leader_anchor((-100.0, -100.0 * t * 0.999), box) == (-30, 0)
    assert leader_anchor((100.0 * t, -100.0), box) == (30, -10)
    assert leader_anchor((-100.0 * t * 0.999, -100.0), box) == (0, -10)


def test_the_octant_depends_on_direction_not_on_box_shape():
    wide = Rect(0, 0, 400, 10)
    tall = Rect(0, 0, 10, 400)
    # 45 degrees from either centre is a corner, however flat or tall the box is
    for box in (wide, tall):
        cx, cy = box.center
        assert leader_anchor((cx + 1000, cy + 1000), box) == (box.x1, box.y1)
        assert leader_anchor((cx - 1000, cy - 1000), box) == (box.x0, box.y0)


def test_a_pole_at_the_centre_falls_back_to_the_nearest_point():
    assert leader_anchor(BOX.center, BOX) == BOX.center


def test_build_leader_ends_gap_short_of_the_anchor_on_the_line_to_it():
    for degrees in range(0, 360, 45):
        pole = pole_at(degrees)
        start, end = build_leader(pole, BOX, 2.0)
        target = leader_anchor(pole, BOX)
        assert start == pole
        assert math.dist(end, target) == pytest.approx(2.0)
        assert math.dist(pole, end) + 2.0 == pytest.approx(math.dist(pole, target))


def test_follow_leader_reanchors_when_the_label_moves():
    leader = build_leader(pole_at(0), BOX, 2.0)  # the pole is right of the box: anchor 5
    moved = BOX.shifted(150, 150)  # now the pole is below-left of the box: anchor 6
    start, end = follow_leader(leader, moved)
    assert start == leader[0]
    assert math.dist(end, leader_anchor(start, moved)) == pytest.approx(2.0)
    assert leader_anchor(start, moved) != leader_anchor(start, BOX)


def test_callout_search_ranks_leaders_that_end_at_the_anchor():
    region = ((100.0, 100.0), (110.0, 100.0), (110.0, 110.0), (100.0, 110.0))
    placement = place_callout(region, (40, 12), Obstacles(polygons=(region,)), Rect(0, 0, 300, 300))
    assert placement.violations == 0
    start, end = placement.leader
    assert math.dist(end, leader_anchor(start, placement.rect)) == pytest.approx(2.0)


@pytest.mark.parametrize("size", [(40, 12), (300, 10), (300, 40), (10, 300), (200, 100)])
def test_a_placed_leader_never_runs_through_its_own_label(size):
    region = ((100.0, 100.0), (110.0, 100.0), (110.0, 110.0), (100.0, 110.0))
    wall = ((125.0, 0.0), (125.0, 300.0))
    for obstacles in (
        Obstacles(polygons=(region,)),
        Obstacles(segments=(wall,), polygons=(region,)),
    ):
        placement = place_callout(region, size, obstacles, Rect(0, 0, 600, 600))
        assert not rect_hits_segment(placement.rect.inflate(-1.0), *placement.leader)
