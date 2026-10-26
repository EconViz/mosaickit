import math

import pytest

from mosaickit.errors import ConfigurationError
from mosaickit.layout import (
    Rect,
    axis_span_for_display_slope,
    centered_view,
    chord_to_rect,
    clip_polyline,
    clip_polyline_fragments,
    clip_segment,
    data_slope_for_display,
    display_slope,
    extend_chord,
    extend_line_through,
    line_through_display_angle,
    line_through_display_slope,
)


def test_clip_segment_crossing_inside_and_outside():
    rect = Rect(0, 0, 10, 8)
    assert clip_segment((-2, 2), (12, 2), rect) == ((0, 2), (10, 2))
    assert clip_segment((2, 2), (8, 6), rect) == ((2, 2), (8, 6))
    assert clip_segment((-2, -1), (12, -1), rect) is None


def test_clip_segment_accepts_reversed_rect_and_zero_length_segments():
    rect = Rect(10, 8, 0, 0)
    assert clip_segment((4, 3), (4, 3), rect) == ((4, 3), (4, 3))
    assert clip_segment((-1, 3), (-1, 3), rect) is None
    assert clip_segment((5, -5), (5, 12), rect) == ((5, 0), (5, 8))


def test_clip_polyline_preserves_separate_visible_fragments():
    fragments = clip_polyline_fragments(
        [(-1, 1), (1, 1), (3, 1), (3, 3), (1, 1)],
        Rect(0, 0, 2, 2),
    )
    assert fragments == (
        ((0, 1), (1, 1), (2, 1)),
        ((2, 2), (1, 1)),
    )


def test_clip_polyline_returns_empty_when_no_segment_enters():
    assert clip_polyline_fragments([(-2, -2), (-1, -1), (-2, -1)], Rect(0, 0, 2, 2)) == ()


def test_extend_chord_by_absolute_distance():
    assert extend_chord([(1, 1), (4, 5)], before=5, after=10) == (
        (-2, -3),
        (10, 13),
    )


def test_extend_chord_by_fraction_of_solved_span():
    segment = extend_chord([(2, 1), (6, 3)], before=0.25, relative=True)
    assert segment[0] == pytest.approx((1, 0.5))
    assert segment[1] == pytest.approx((7, 3.5))


def test_extend_chord_supports_vertical_lines_and_rejects_degenerate_chords():
    assert extend_chord([(3, 2), (3, 8)], before=2, after=1) == ((3, 0), (3, 9))
    with pytest.raises(ValueError, match="distinct"):
        extend_chord([(1, 1), (1, 1)])
    with pytest.raises(ValueError, match="non-negative"):
        extend_chord([(0, 0), (1, 1)], before=-1)


@pytest.mark.parametrize(
    "points, expected",
    [
        ([(2, 2), (8, 8)], ((0, 0), (10, 10))),
        ([(4, 2), (4, 8)], ((4, 0), (4, 10))),
        ([(2, 6), (8, 6)], ((0, 6), (10, 6))),
    ],
)
def test_chord_to_rect_extends_diagonal_vertical_and_horizontal_lines(points, expected):
    segment = chord_to_rect(points, Rect(0, 0, 10, 10))
    assert segment is not None
    assert segment[0] == pytest.approx(expected[0])
    assert segment[1] == pytest.approx(expected[1])


def test_chord_to_rect_returns_none_when_infinite_line_misses_rect():
    assert chord_to_rect([(0, 20), (1, 21)], Rect(0, 0, 10, 10)) is None


def _apparent_slope(segment, data_rect, display_rect):
    (x0, y0), (x1, y1) = segment
    display_dx = (x1 - x0) / data_rect.width * display_rect.width
    display_dy = (y1 - y0) / data_rect.height * display_rect.height
    return display_dy / display_dx


def test_display_slope_accounts_for_non_square_data_and_display_extents():
    data_rect = Rect(0, -10, 100, 10)
    display_rect = Rect(0, 0, 200, 400)
    segment = line_through_display_slope(
        (50, 0),
        -2,
        data_rect=data_rect,
        display_rect=display_rect,
    )
    assert segment is not None
    assert _apparent_slope(segment, data_rect, display_rect) == pytest.approx(-2)
    midpoint = ((segment[0][0] + segment[1][0]) / 2, (segment[0][1] + segment[1][1]) / 2)
    assert midpoint == pytest.approx((50, 0))


def test_infinite_display_slope_constructs_vertical_line():
    segment = line_through_display_slope(
        (3, 4),
        math.inf,
        data_rect=Rect(0, 0, 10, 8),
        display_rect=Rect(0, 0, 1000, 100),
    )
    assert segment == ((3, 0), (3, 8))


@pytest.mark.parametrize("angle", [90, 270, -90])
def test_display_angle_constructs_exact_vertical_line(angle):
    segment = line_through_display_angle(
        (3, 4),
        angle,
        data_rect=Rect(0, 0, 10, 8),
        display_rect=Rect(0, 0, 1000, 100),
    )
    assert segment is not None
    assert segment[0] == pytest.approx((3, 0))
    assert segment[1] == pytest.approx((3, 8))


def test_display_angle_has_requested_apparent_angle_on_non_square_panel():
    data_rect = Rect(-50, -5, 50, 5)
    display_rect = Rect(10, 20, 610, 220)
    segment = line_through_display_angle(
        (0, 0),
        30,
        data_rect=data_rect,
        display_rect=display_rect,
    )
    assert segment is not None
    expected = math.tan(math.radians(30))
    assert _apparent_slope(segment, data_rect, display_rect) == pytest.approx(expected)


@pytest.mark.parametrize(
    "function, value, message",
    [
        (line_through_display_slope, math.nan, "NaN"),
        (line_through_display_angle, math.inf, "finite"),
    ],
)
def test_display_line_rejects_invalid_slope_or_angle(function, value, message):
    with pytest.raises(ValueError, match=message):
        function(
            (1, 1),
            value,
            data_rect=Rect(0, 0, 2, 2),
            display_rect=Rect(0, 0, 20, 20),
        )


def test_display_line_rejects_degenerate_coordinate_extents():
    with pytest.raises(ValueError, match="positive width"):
        line_through_display_slope(
            (1, 1),
            1,
            data_rect=Rect(0, 0, 0, 2),
            display_rect=Rect(0, 0, 20, 20),
        )


def test_clip_polyline_returns_single_visible_path_in_either_range_order():
    path = [(-1, 1), (1, 1), (3, 3)]
    assert clip_polyline(path, (0, 2), (0, 2)) == ((0, 1), (1, 1), (2, 2))
    assert clip_polyline(path, (2, 0), (2, 0)) == ((0, 1), (1, 1), (2, 2))
    assert clip_polyline([(5, 5), (6, 6)], (0, 1), (0, 1)) == ()


def test_clip_polyline_rejects_reentry_and_bad_input():
    with pytest.raises(ConfigurationError, match="re-enters"):
        clip_polyline([(-1, 1), (3, 1), (3, 3), (1, 1)], (0, 2), (0, 2))
    with pytest.raises(ConfigurationError, match="two points"):
        clip_polyline([(0, 0)], (0, 1), (0, 1))
    with pytest.raises(ConfigurationError, match="finite"):
        clip_polyline([(0, 0), (math.nan, 1)], (0, 1), (0, 1))


def test_extend_line_through_uses_shares_of_chord_length():
    assert extend_line_through([(0, 0), (3, 4)], before=1, after=0.5) == (
        pytest.approx((-3, -4)),
        pytest.approx((4.5, 6)),
    )
    assert extend_line_through([(1, 0), (5, 5), (3, 4)], before=0.5)[0] == pytest.approx((0, -2))
    assert extend_line_through([(2, 1), (2, 3)], before=0.5) == ((2, 0), (2, 4))
    with pytest.raises(ConfigurationError, match="distinct"):
        extend_line_through([(1, 1), (1, 1)], before=0.5)


def test_display_slope_round_trips_and_matches_formula():
    assert display_slope(2, 10, 5, 4, 2) == pytest.approx(2 * (10 / 5) * (2 / 4))
    assert data_slope_for_display(display_slope(2, 10, 5, 4, 2), 10, 5, 4, 2) == pytest.approx(2)
    assert display_slope(0, 1, 1, 1, 1) == 0
    assert display_slope(-1.5, 1, 1, 1, 1) == -1.5


@pytest.mark.parametrize("bad", [0, -1, math.inf, math.nan])
def test_slope_conversions_reject_degenerate_spans_and_sizes(bad):
    with pytest.raises(ConfigurationError, match="positive"):
        display_slope(1, bad, 1, 1, 1)
    with pytest.raises(ConfigurationError, match="positive"):
        data_slope_for_display(1, 1, bad, 1, 1)
    with pytest.raises(ConfigurationError, match="positive"):
        axis_span_for_display_slope(1, 1, 1, bad, 1)


def test_axis_span_for_display_slope_produces_requested_slope():
    y_span = axis_span_for_display_slope(-3, 8, 0.9, 5, 4)
    assert y_span > 0
    assert display_slope(3, 8, y_span, 5, 4) == pytest.approx(0.9)
    with pytest.raises(ConfigurationError, match="non-zero"):
        axis_span_for_display_slope(0, 8, 0.9, 5, 4)
    with pytest.raises(ConfigurationError, match="non-zero"):
        axis_span_for_display_slope(1, 8, 0, 5, 4)


def test_centered_view_centres_midpoint_with_gap_share():
    view = centered_view([(10, 4), (14, 8)], gap_share=0.25)
    assert (view.x_span, view.y_span) == (16, 16)
    assert (view.x_origin + view.x_span / 2, view.y_origin + view.y_span / 2) == (12, 6)
    assert view.shift((12, 6)) == (8, 8)


def test_centered_view_with_display_slope_and_explicit_data_slope():
    view = centered_view(
        [(10, 4), (14, 8)], gap_share=0.25, display_slope=0.9, data_slope=0.5, width=5, height=4
    )
    assert view.x_span == 16
    assert display_slope(0.5, view.x_span, view.y_span, 5, 4) == pytest.approx(0.9)
    assert view.y_origin + view.y_span / 2 == pytest.approx(6)
    chord = centered_view([(10, 4), (14, 8)], gap_share=0.25, display_slope=0.9)
    assert display_slope(1, chord.x_span, chord.y_span, 1, 1) == pytest.approx(0.9)


def test_centered_view_rejects_degenerate_input():
    with pytest.raises(ConfigurationError, match="horizontal"):
        centered_view([(1, 1), (1, 5)], gap_share=0.2)  # vertical line
    with pytest.raises(ConfigurationError, match="vertical"):
        centered_view([(1, 1), (5, 1)], gap_share=0.2)
    with pytest.raises(ConfigurationError, match="horizontal"):
        centered_view([(2, 2), (2, 2)], gap_share=0.2, display_slope=1)
    with pytest.raises(ConfigurationError, match="gap_share"):
        centered_view([(1, 1), (2, 2)], gap_share=0)
    with pytest.raises(ConfigurationError, match="gap_share"):
        centered_view([(1, 1), (2, 2)], gap_share=1.5)
    with pytest.raises(ConfigurationError, match="two points"):
        centered_view([(1, 1)], gap_share=0.2)
    with pytest.raises(ConfigurationError, match="non-zero"):
        centered_view([(1, 1), (5, 1)], gap_share=0.2, display_slope=1)
