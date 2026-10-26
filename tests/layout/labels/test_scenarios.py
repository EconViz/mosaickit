"""The failures that motivated the engine, reproduced with synthetic figures."""

from __future__ import annotations

import pytest
from helpers import violations
from scenes import CANVAS, lm_lines

from mosaickit.errors import ConfigurationError
from mosaickit.layout import Rect
from mosaickit.layout.labels import Label, LabelOptions, Obstacle, place_labels


def _distance(box: Rect, point: tuple[float, float]) -> float:
    near = box.nearest_point(point)
    return abs(near[0] - point[0]) + abs(near[1] - point[1])


def test_three_parallel_lines_each_name_stays_with_its_own_line() -> None:
    labels, obstacles = lm_lines()
    options = LabelOptions()
    result = place_labels(labels, obstacles, CANVAS, options)
    assert result.ok and all(p.ok for p in result.placements)
    assert violations(result, labels, obstacles, CANVAS, options) == []
    placements = result.by_id()
    for label in labels:
        placed = placements[label.id]
        if placed.leader is not None:  # a leader states whom the name belongs to
            assert placed.leader[0] == label.anchor
            continue
        box = placed.box
        own = _distance(box, label.anchor)
        for other in labels:
            if other.id != label.id:
                assert own < _distance(box, other.anchor), f"{label.id} nearer {other.id}"


def test_three_parallel_lines_on_a_roomy_canvas_need_no_leader() -> None:
    labels, obstacles = lm_lines()
    roomy = Rect(0.0, 0.0, 460.0, 300.0)
    result = place_labels(labels, obstacles, roomy)
    assert result.ok and all(p.leader is None for p in result.placements)
    assert [p.side for p in result.placements].count("upper-right") >= 1


def test_three_parallel_lines_are_stable_under_input_order() -> None:
    labels, obstacles = lm_lines()
    forward = place_labels(labels, obstacles, CANVAS).by_id()
    backward = place_labels(labels[::-1], obstacles, CANVAS).by_id()
    assert {k: v.box.center for k, v in forward.items()} == {
        k: v.box.center for k, v in backward.items()
    }


def test_the_first_side_is_used_when_it_is_free() -> None:
    label = Label("a", (100.0, 100.0), (40.0, 20.0), sides=("upper-right", "right"))
    placed = place_labels([label], [], CANVAS).placements[0]
    assert placed.side == "upper-right" and placed.leader is None
    assert placed.text_anchor == "bottom-left"
    assert placed.offset == (5.0, 5.0)


def test_a_blocked_first_side_falls_to_the_next_free_one() -> None:
    label = Label("a", (100.0, 100.0), (40.0, 20.0), sides=("upper-right", "lower-right"))
    wall = Obstacle.rect(Rect(100.0, 104.0, 300.0, 140.0))
    placed = place_labels([label], [wall], CANVAS).placements[0]
    assert placed.ok and placed.side == "lower-right"


def test_a_boxed_in_label_gets_a_leader() -> None:
    enclosure = Obstacle.polyline([(150, 120), (210, 120), (210, 160), (150, 160), (150, 120)])
    options = LabelOptions(leader_after=10.0, leader_crossing_weight=0.0)
    label = Label("a", (180.0, 140.0), (30.0, 12.0))
    placed = place_labels([label], [enclosure], CANVAS, options).placements[0]
    assert placed.ok and placed.leader is not None
    assert placed.leader[0] == (180.0, 140.0)


def test_an_infeasible_label_warns_instead_of_overlapping() -> None:
    label = Label("a", (50.0, 50.0), (500.0, 20.0))  # wider than the canvas
    result = place_labels([label], [], CANVAS)
    assert not result.ok
    assert result.warnings[0].label_id == "a" and result.warnings[0].reason == "no-free-position"
    assert result.placements[0].ok is False


def test_two_labels_that_cannot_both_fit_report_a_warning() -> None:
    bounds = Rect(0.0, 0.0, 60.0, 30.0)
    labels = [
        Label("a", (10.0, 15.0), (40.0, 20.0), sides=("right",)),
        Label("b", (12.0, 15.0), (40.0, 20.0), sides=("right",)),
    ]
    result = place_labels(labels, [], bounds, LabelOptions(rings=0))
    assert result.warnings
    assert sum(1 for p in result.placements if p.ok) <= 1


def _ticks(xs: list[tuple[str, float]], width: float) -> list[Label]:
    return [
        Label(n, (x, 100.0), (width, 14.0), sides=("below", "above"), spread="stack") for n, x in xs
    ]


def test_colliding_ticks_are_staggered_or_flipped_never_overlapped() -> None:
    axis = Obstacle.polyline([(0.0, 100.0), (360.0, 100.0)])
    ticks = _ticks([("W0", 100.0), ("W1", 108.0), ("N1", 114.0)], 22.0)
    options = LabelOptions()
    result = place_labels(ticks, [axis], CANVAS, options)
    assert result.ok
    assert violations(result, ticks, [axis], CANVAS, options) == []
    assert len({(p.side, round(p.offset[1])) for p in result.placements}) == 3


@pytest.mark.parametrize("strategy", ["stagger", "opposite", "stagger+opposite"])
def test_each_tick_strategy_separates_two_close_ticks(strategy: str) -> None:
    axis = Obstacle.polyline([(0.0, 100.0), (360.0, 100.0)])
    ticks = _ticks([("a", 100.0), ("b", 106.0)], 22.0)
    options = LabelOptions(tick_strategy=strategy)
    result = place_labels(ticks, [axis], CANVAS, options)
    assert violations(result, ticks, [axis], CANVAS, options) == []
    assert result.ok
    if strategy == "opposite":
        assert {p.side for p in result.placements} == {"below", "above"}


def test_wider_labels_make_more_room_not_overlap() -> None:
    axis = Obstacle.polyline([(0.0, 100.0), (360.0, 100.0)])
    for width in (22.0, 60.0, 120.0):
        ticks = _ticks([("a", 100.0), ("b", 110.0)], width)
        result = place_labels(ticks, [axis], CANVAS)
        assert violations(result, ticks, [axis], CANVAS, LabelOptions()) == []


def test_options_are_validated() -> None:
    with pytest.raises(ConfigurationError):
        LabelOptions(tick_strategy="spiral")
    with pytest.raises(ConfigurationError):
        LabelOptions(gap=-1.0)
    with pytest.raises(ValueError):
        place_labels([Label("a", (1, 1), (1, 1)), Label("a", (2, 2), (1, 1))], [], CANVAS)


def test_a_label_never_covers_another_labels_anchor() -> None:
    a = Label("a", (100.0, 100.0), (60.0, 20.0), sides=("right",))
    b = Label("b", (130.0, 106.0), (10.0, 10.0))
    result = place_labels([a, b], [], CANVAS)
    assert not result.placements[0].box.contains(b.anchor)
