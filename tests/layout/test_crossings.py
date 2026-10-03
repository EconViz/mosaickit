import pytest

from mosaickit.layout.placement.crossings import beyond_crossings, region_crossings

# Region whose right vertex is the crossing X = (150, 150) of two lines.
REGION = ((120.0, 140.0), (120.0, 160.0), (150.0, 150.0))
LINE_A = ((90.0, 130.0), (210.0, 170.0))
LINE_B = ((90.0, 170.0), (210.0, 130.0))


def test_proper_crossing_on_the_region_is_found():
    (x,) = region_crossings(REGION, (LINE_A, LINE_B), tolerance=1.5)
    assert x == pytest.approx((150, 150))


def test_endpoint_contact_is_not_a_crossing():
    starts_on_a = ((150.0, 150.0), (150.0, 300.0))  # begins exactly on LINE_A
    assert region_crossings(REGION, (LINE_A, starts_on_a), tolerance=1.5) == ()


def test_crossings_far_from_the_region_are_ignored():
    far_a = ((0.0, 0.0), (20.0, 20.0))
    far_b = ((0.0, 20.0), (20.0, 0.0))
    assert region_crossings(REGION, (far_a, far_b), tolerance=1.5) == ()


def test_beyond_counts_points_past_each_crossing():
    pole = (130.0, 150.0)
    crossings = ((150.0, 150.0),)
    assert beyond_crossings((180.0, 200.0), pole, crossings) == 1  # right of X
    assert beyond_crossings((140.0, 80.0), pole, crossings) == 0  # left of X
