import math

import pytest

from mosaickit.layout.geometry import brace_outline


def _flat(points):
    return [v for point in points for v in point]


def _xs(brace):
    return [p[0] for p in brace.points]


def _ys(brace):
    return [p[1] for p in brace.points]


def test_vertical_brace_spans_start_to_end_and_points_along_direction():
    brace = brace_outline(10, 110, base=50, depth=8, direction=1, axis="y")
    ys = _ys(brace)
    assert ys[0] == pytest.approx(10) and ys[-1] == pytest.approx(110)
    assert ys == sorted(ys)
    assert min(_xs(brace)) == pytest.approx(50)
    assert max(_xs(brace)) == pytest.approx(58)
    assert brace.tip == pytest.approx((58, 60))
    # Both ends sit on the base line; the tip is the only point at full depth.
    assert brace.points[0][0] == pytest.approx(50) and brace.points[-1][0] == pytest.approx(50)


def test_brace_is_symmetric_about_its_middle():
    brace = brace_outline(0, 100, base=0, depth=10, direction=1, axis="y")
    for (xa, ya), (xb, yb) in zip(brace.points, reversed(brace.points), strict=True):
        assert xa == pytest.approx(xb)
        assert ya + yb == pytest.approx(100)


def test_negative_direction_mirrors_the_brace():
    right = brace_outline(0, 100, base=20, depth=8, direction=1, axis="y")
    left = brace_outline(0, 100, base=20, depth=8, direction=-1, axis="y")
    for (xr, yr), (xl, yl) in zip(right.points, left.points, strict=True):
        assert yr == pytest.approx(yl)
        assert xr - 20 == pytest.approx(20 - xl)
    assert left.tip == pytest.approx((12, 50))


def test_horizontal_brace_swaps_the_coordinates():
    vertical = brace_outline(0, 100, base=5, depth=8, direction=-1, axis="y")
    horizontal = brace_outline(0, 100, base=5, depth=8, direction=-1, axis="x")
    assert _flat((y, x) for x, y in vertical.points) == pytest.approx(_flat(horizontal.points))
    assert horizontal.tip == pytest.approx((50, -3))


def test_reversed_span_is_normalised():
    reversed_span = brace_outline(100, 0, base=0, depth=8, direction=1)
    assert _flat(reversed_span.points) == pytest.approx(
        _flat(brace_outline(0, 100, base=0, depth=8, direction=1).points)
    )


def test_short_span_shrinks_the_arcs_instead_of_overshooting():
    brace = brace_outline(0, 8, base=0, depth=10, direction=1)
    ys = _ys(brace)
    assert ys == sorted(ys)
    assert min(ys) == pytest.approx(0) and max(ys) == pytest.approx(8)
    assert all(math.isfinite(v) for p in brace.points for v in p)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"start": 1, "end": 1},
        {"depth": 0},
        {"direction": 0},
        {"axis": "z"},
    ],
)
def test_invalid_braces_are_rejected(kwargs):
    arguments = {"start": 0, "end": 10, "base": 0, "depth": 4, "direction": 1, "axis": "y"}
    arguments.update(kwargs)
    start, end = arguments.pop("start"), arguments.pop("end")
    with pytest.raises(ValueError):
        brace_outline(start, end, **arguments)
