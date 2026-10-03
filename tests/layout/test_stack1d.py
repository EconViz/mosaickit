import itertools

import pytest

from mosaickit.layout.stack1d import assign_lanes, spread


def _assert_separated(centers, sizes, gap):
    order = sorted(range(len(centers)), key=lambda i: centers[i])
    for i, j in itertools.pairwise(order):
        assert centers[j] - sizes[j] / 2 >= centers[i] + sizes[i] / 2 + gap - 1e-9


def test_items_that_do_not_overlap_stay_put():
    assert spread([0, 20, 40], [10, 10, 10], gap=2) == pytest.approx((0, 20, 40))


def test_overlapping_pair_moves_apart_symmetrically():
    result = spread([10, 12], [10, 10], gap=2)
    assert result == pytest.approx((5, 17))
    assert sum(result) / 2 == pytest.approx(11)


def test_order_is_kept_and_overlap_removed():
    centers = [30, 5, 6, 7, 31, 100]
    sizes = [12, 8, 8, 8, 4, 10]
    result = spread(centers, sizes, gap=3)
    _assert_separated(result, sizes, 3)
    assert sorted(range(6), key=lambda i: result[i]) == sorted(range(6), key=lambda i: centers[i])


def test_equal_centres_keep_input_order():
    result = spread([0, 0, 0], [2, 2, 2], gap=0)
    assert result == pytest.approx((-2, 0, 2))


def test_only_the_crowded_cluster_moves():
    result = spread([0, 1, 50], [4, 4, 4], gap=0)
    assert result[2] == pytest.approx(50)
    assert result[0] + result[1] == pytest.approx(1)


def test_displacement_is_minimal_against_brute_force():
    # For two items the optimum keeps their mean; a third far item stays.
    centers, sizes, gap = [0.0, 3.0, 4.0], [4.0, 4.0, 4.0], 1.0
    result = spread(centers, sizes, gap)
    _assert_separated(result, sizes, gap)
    cost = sum((a - b) ** 2 for a, b in zip(result, centers, strict=True))
    best = min(
        sum((a - b) ** 2 for a, b in zip((s - 5, s, s + 5), centers, strict=True))
        for s in [i / 100 for i in range(-500, 1000)]
    )
    assert cost == pytest.approx(best, abs=1e-3)


def test_merged_cluster_pulls_in_its_neighbour():
    # Merging the first two pushes their block into the third, which then joins it.
    result = spread([0, 0, 8], [6, 6, 6], gap=0)
    _assert_separated(result, [6, 6, 6], 0)
    assert result[2] > 8
    assert sum(result) / 3 == pytest.approx(8 / 3)


def test_spread_handles_empty_and_rejects_mismatched_input():
    assert spread([], [], gap=1) == ()
    with pytest.raises(ValueError):
        spread([1, 2], [1], gap=0)
    with pytest.raises(ValueError):
        spread([1], [-1], gap=0)


def test_lanes_put_overlapping_intervals_side_by_side():
    assert assign_lanes([(0, 10), (12, 20), (5, 15), (21, 30)], gap=1) == (0, 0, 1, 0)


def test_lanes_respect_the_gap():
    assert assign_lanes([(0, 10), (10.5, 20)], gap=1) == (0, 1)
    assert assign_lanes([(0, 10), (11, 20)], gap=1) == (0, 0)


def test_lanes_accept_reversed_intervals():
    assert assign_lanes([(10, 0), (5, 15)]) == (0, 1)
