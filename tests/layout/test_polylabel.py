import math

import pytest

from mosaickit.layout.geometry import polylabel


def test_polylabel_square_is_its_center():
    pole = polylabel(((0, 0), (10, 0), (10, 10), (0, 10)), precision=0.01)
    assert pole == pytest.approx((5, 5), abs=0.05)


def test_polylabel_thin_triangle_is_its_incenter():
    # Legs 100 and 10: inradius = area / semiperimeter = 500 / 105.25 ≈ 4.75
    pole = polylabel(((0, 0), (100, 0), (0, 10)), precision=0.01)
    assert math.dist(pole, (4.75, 4.75)) < 0.1


def test_polylabel_degenerate_polygon_returns_first_point():
    assert polylabel(((1, 1), (1, 1), (1, 1))) == (1, 1)
