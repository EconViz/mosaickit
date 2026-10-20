import pytest

from mosaickit import ArrowStyle, DashStyle


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("-", DashStyle.SOLID),
        ("--", DashStyle.DASHED),
        (":", DashStyle.DOTTED),
        ("-.", DashStyle.DASHDOT),
    ],
)
def test_dash_style_accepts_short_forms(value, expected):
    assert DashStyle(value) is expected


def test_dash_style_still_rejects_unknown_values():
    with pytest.raises(ValueError):
        DashStyle("wavy")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("->", ArrowStyle.OPEN),
        ("-|>", ArrowStyle.TRIANGLE),
        ("open", ArrowStyle.OPEN),
        ("wedge", ArrowStyle.WEDGE),
    ],
)
def test_arrow_style_accepts_matplotlib_spellings(value, expected):
    assert ArrowStyle(value) is expected


def test_simple_is_another_name_for_open():
    assert ArrowStyle.SIMPLE is ArrowStyle.OPEN
    assert [style.name for style in ArrowStyle] == ["OPEN", "TRIANGLE", "FANCY", "WEDGE"]
