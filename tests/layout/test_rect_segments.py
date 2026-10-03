import pytest

from mosaickit.layout.geometry import Rect, rect_hits_segment, segments_intersect


def test_rect_basics():
    rect = Rect.centered((10, 20), 4, 2)
    assert rect == Rect(8, 19, 12, 21)
    assert rect.width == 4 and rect.height == 2
    assert rect.center == (10, 20)
    assert rect.inflate(1) == Rect(7, 18, 13, 22)
    assert rect.contains((8, 19)) and not rect.contains((7.9, 19))
    assert rect.within(Rect(0, 0, 100, 100))
    assert not rect.within(Rect(9, 0, 100, 100))
    assert rect.intersects(Rect(11, 20, 30, 30))
    assert not rect.intersects(Rect(13, 0, 30, 30))
    assert rect.nearest_point((0, 0)) == (8, 19)
    assert rect.nearest_point((10, 20)) == (10, 20)
    assert len(rect.edges()) == 4


@pytest.mark.parametrize(
    "a,b,c,d,expected",
    [
        ((0, 0), (10, 10), (0, 10), (10, 0), True),  # proper crossing
        ((0, 0), (10, 0), (0, 1), (10, 1), False),  # parallel
        ((0, 0), (10, 0), (10, 0), (10, 5), True),  # endpoint touch
        ((0, 0), (10, 0), (5, 0), (15, 0), True),  # collinear overlap
        ((0, 0), (4, 0), (5, 0), (15, 0), False),  # collinear, disjoint
        ((0, 0), (4, 4), (5, 0), (5, 10), False),  # stops short
    ],
)
def test_segments_intersect(a, b, c, d, expected):
    assert segments_intersect(a, b, c, d) is expected
    assert segments_intersect(c, d, a, b) is expected


def test_rect_hits_segment():
    rect = Rect(0, 0, 10, 10)
    assert rect_hits_segment(rect, (-5, 5), (15, 5))  # passes through
    assert rect_hits_segment(rect, (2, 2), (3, 3))  # fully inside
    assert not rect_hits_segment(rect, (-5, -5), (-1, 20))  # outside
