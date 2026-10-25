import math

import pytest

from mosaickit.layout import (
    Obstacles,
    Rect,
    extend_polyline_tail,
    place_rotation_marker,
    tail_label_position,
)


def radial_point(pivot, degrees, radius):
    angle = math.radians(degrees)
    return pivot[0] + radius * math.cos(angle), pivot[1] + radius * math.sin(angle)


def quadratic_connector(start, end, pivot):
    midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    control = ((midpoint[0] + pivot[0]) / 2, (midpoint[1] + pivot[1]) / 2)
    return tuple(
        (
            (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t**2 * end[0],
            (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t**2 * end[1],
        )
        for t in (index / 24 for index in range(25))
    )


def ray(pivot, degrees, radius=100):
    return pivot, radial_point(pivot, degrees, radius)


def test_rotation_search_starts_at_tail_and_stays_inside_bounds() -> None:
    pivot = (50, 50)
    placement = place_rotation_marker(
        ray(pivot, 0),
        ray(pivot, 15),
        pivot,
        Rect(0, 0, 135, 150),
        quadratic_connector,
        search_step=1,
        minimum_span=5,
    )

    assert placement is not None
    assert placement.fraction < 1
    assert placement.radius == pytest.approx(85)
    assert all(Rect(0, 0, 135, 150).contains(point) for point in placement.path)


def test_later_rotation_marker_moves_inward_to_clear_earlier_one() -> None:
    pivot = (120, 80)
    bounds = Rect(0, 0, 240, 200)
    first = place_rotation_marker(
        ray(pivot, 150),
        ray(pivot, 135),
        pivot,
        bounds,
        quadratic_connector,
        clearance=8,
        minimum_span=5,
    )
    assert first is not None
    second = place_rotation_marker(
        ray(pivot, 135),
        ray(pivot, 120),
        pivot,
        bounds,
        quadratic_connector,
        accepted=(first.path,),
        clearance=8,
        minimum_span=5,
    )

    assert second is not None
    assert second.radius < first.radius
    assert second.fraction < first.fraction


def test_touching_earlier_marker_is_rejected_with_zero_clearance() -> None:
    pivot = (120, 80)
    bounds = Rect(0, 0, 240, 200)
    first = place_rotation_marker(
        ray(pivot, 150), ray(pivot, 135), pivot, bounds, quadratic_connector
    )
    assert first is not None
    second = place_rotation_marker(
        ray(pivot, 135),
        ray(pivot, 120),
        pivot,
        bounds,
        quadratic_connector,
        accepted=(first.path,),
    )

    assert second is not None
    assert second.radius < first.radius


def test_obstacle_can_force_search_inward_or_exhaust_candidates() -> None:
    pivot = (20, 20)
    old, new = ray(pivot, 0), ray(pivot, 20)
    bounds = Rect(0, 0, 140, 140)
    outer_obstacle = Obstacles(rects=(Rect(100, 20, 130, 60),))
    placement = place_rotation_marker(
        old,
        new,
        pivot,
        bounds,
        quadratic_connector,
        obstacles=outer_obstacle,
        minimum_span=5,
    )

    assert placement is not None
    assert placement.fraction < 0.8
    assert (
        place_rotation_marker(
            old,
            new,
            pivot,
            bounds,
            quadratic_connector,
            obstacles=Obstacles(rects=(bounds,)),
            minimum_span=5,
        )
        is None
    )


def test_swapping_paths_reverses_connector() -> None:
    pivot = (50, 50)
    bounds = Rect(0, 0, 200, 200)
    forward = place_rotation_marker(
        ray(pivot, 0), ray(pivot, 20), pivot, bounds, quadratic_connector
    )
    reverse = place_rotation_marker(
        ray(pivot, 20), ray(pivot, 0), pivot, bounds, quadratic_connector
    )

    assert forward is not None and reverse is not None
    for actual, expected in zip(reverse.path, reversed(forward.path), strict=True):
        assert actual == pytest.approx(expected)


def test_uniform_scaling_preserves_selected_fraction() -> None:
    pivot = (50, 50)
    placement = place_rotation_marker(
        ray(pivot, 0),
        ray(pivot, 15),
        pivot,
        Rect(0, 0, 135, 150),
        quadratic_connector,
        search_step=1,
    )
    scale = 3
    scaled = place_rotation_marker(
        tuple((scale * x, scale * y) for x, y in ray(pivot, 0)),
        tuple((scale * x, scale * y) for x, y in ray(pivot, 15)),
        (scale * pivot[0], scale * pivot[1]),
        Rect(0, 0, 135 * scale, 150 * scale),
        quadratic_connector,
        search_step=scale,
    )

    assert placement is not None and scaled is not None
    assert scaled.fraction == pytest.approx(placement.fraction)
    for actual, expected in zip(scaled.path, placement.path, strict=True):
        assert actual == pytest.approx((scale * expected[0], scale * expected[1]))


def test_tail_extension_and_label_position_follow_display_tangent() -> None:
    path = ((0, 0), (10, 10))
    extended = extend_polyline_tail(path, math.sqrt(8))
    assert extended[-1] == pytest.approx((12, 12))

    position = tail_label_position(path, (20, 8), gap=2)
    tangent = (10, 10)
    offset = (position[0] - 10, position[1] - 10)
    assert tangent[0] * offset[1] - tangent[1] * offset[0] == pytest.approx(0)
    label = Rect(position[0] - 10, position[1], position[0] + 10, position[1] + 8)
    assert not label.inflate(2).contains(path[-1])
    assert extend_polyline_tail(path, 0) == path


@pytest.mark.parametrize("distance", [-1, math.inf])
def test_tail_extension_rejects_invalid_distance(distance) -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        extend_polyline_tail(((0, 0), (1, 1)), distance)
