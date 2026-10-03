import pytest

from mosaickit.layout.gutter import Band, gutter_columns


def test_marks_then_braces_then_notes_outward():
    columns = gutter_columns(12, [20, 15], 40, start=6, gap=8)
    assert columns.marks == Band(6, 18)
    assert columns.braces == (Band(26, 46), Band(54, 69))
    assert columns.notes == Band(77, 117)
    assert columns.extent == 117


def test_empty_columns_collapse_without_gaps():
    columns = gutter_columns(0, [], 30, start=6, gap=8)
    assert columns.marks.width == 0
    assert columns.notes == Band(6, 36)
    assert gutter_columns(10, [], 0, start=6, gap=8).extent == 16
    assert gutter_columns(0, [], 0, start=6, gap=8).extent == 6


def test_braces_without_marks_start_at_the_axis_gap():
    columns = gutter_columns(0, [10], 5, start=4, gap=8)
    assert columns.braces == (Band(4, 14),)
    assert columns.notes == Band(22, 27)


def test_band_width():
    assert Band(3, 10).width == 7


def test_negative_widths_are_rejected():
    with pytest.raises(ValueError):
        gutter_columns(-1, [], 0, start=0, gap=0)
