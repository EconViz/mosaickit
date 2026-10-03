import math

import pytest

from mosaickit.layout.geometry import (
    Rect,
    point_in_polygon,
    polygon_edges,
    ray_exit,
    rect_inside_polygon,
    rect_overlaps_polygon,
)

SQUARE = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
TRIANGLE = ((0.0, 0.0), (100.0, 0.0), (0.0, 100.0))


def test_polygon_edges_close_the_ring():
    edges = polygon_edges(SQUARE)
    assert len(edges) == 4
    assert edges[-1] == ((0.0, 10.0), (0.0, 0.0))


def test_point_in_polygon():
    assert point_in_polygon((5, 5), SQUARE)
    assert not point_in_polygon((15, 5), SQUARE)
    assert point_in_polygon((10, 10), TRIANGLE)
    assert not point_in_polygon((60, 60), TRIANGLE)


def test_rect_inside_polygon():
    assert rect_inside_polygon(Rect(10, 10, 30, 20), TRIANGLE)
    assert not rect_inside_polygon(Rect(40, 40, 70, 50), TRIANGLE)  # crosses hypotenuse
    assert not rect_inside_polygon(Rect(-5, 10, 10, 20), TRIANGLE)  # crosses left edge


def test_rect_overlaps_polygon():
    assert rect_overlaps_polygon(Rect(40, 40, 70, 50), TRIANGLE)  # partial
    assert rect_overlaps_polygon(Rect(-10, -10, 200, 200), TRIANGLE)  # polygon inside rect
    assert rect_overlaps_polygon(Rect(1, 1, 2, 2), TRIANGLE)  # rect inside polygon
    assert not rect_overlaps_polygon(Rect(80, 80, 90, 90), TRIANGLE)


def test_ray_exit_distance():
    assert ray_exit((5, 5), (1, 0), SQUARE) == pytest.approx(5)
    diagonal = (1 / math.sqrt(2), 1 / math.sqrt(2))
    assert ray_exit((5, 5), diagonal, SQUARE) == pytest.approx(5 * math.sqrt(2))
    assert ray_exit((50, 50), (1, 0), SQUARE) == 0


def test_distance_to_boundary():
    from mosaickit.layout.geometry import distance_to_boundary

    assert distance_to_boundary((5, 5), SQUARE) == pytest.approx(5)
    assert distance_to_boundary((15, 5), SQUARE) == pytest.approx(5)
    assert distance_to_boundary((10, 3), SQUARE) == 0
