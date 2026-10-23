import math

import pytest

import mosaickit
from mosaickit import (
    BraceLayer,
    ConfigurationError,
    Nudge,
    PointLabelLayer,
    RegionLabelLayer,
    Scene,
    SpanBraceLayer,
    TextLayer,
    nudge_from,
    parse_length,
)
from mosaickit.document import scene_from_dict, scene_to_dict

MM = 72 / 25.4


def test_exports():
    for name in ("Nudge", "nudge_from", "parse_length"):
        assert name in mosaickit.__all__


@pytest.mark.parametrize(
    ("value", "points"),
    [
        (10, 10.0),
        (2.5, 2.5),
        (-3, -3.0),
        ("10pt", 10.0),
        ("-3pt", -3.0),
        ("+4pt", 4.0),
        ("  10 pt ", 10.0),
        (".5pt", 0.5),
        ("1e1pt", 10.0),
        ("10PT", 10.0),
        ("2mm", 2 * MM),
        ("1cm", 10 * MM),
        ("0.1in", 7.2),
        ("-1in", -72.0),
    ],
)
def test_parse_length_units_and_signs(value, points):
    assert parse_length(value) == pytest.approx(points)


def test_parse_length_em_uses_the_font_size():
    assert parse_length("0.5em", font_size=12) == pytest.approx(6.0)
    assert parse_length("-2em", font_size=9.5) == pytest.approx(-19.0)
    assert parse_length("3pt", font_size=12) == 3.0  # font size only matters for em


def test_parse_length_em_without_font_size_is_an_error():
    with pytest.raises(ConfigurationError, match="font size"):
        parse_length("0.5em")


@pytest.mark.parametrize("font_size", [math.nan, -1, "12", True])
def test_parse_length_rejects_a_bad_font_size(font_size):
    with pytest.raises(ConfigurationError):
        parse_length("1em", font_size=font_size)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("10", "unit"),
        ("pt", "Invalid length"),
        ("", "Invalid length"),
        ("10 px", "Unknown length unit 'px'"),
        ("10ptx", "Unknown length unit"),
        ("1-2pt", "Invalid length"),
        ("10pt 2pt", "Invalid length"),
        (True, "number or a string"),
        (None, "NoneType"),
        ((1, 2), "tuple"),
        (math.inf, "finite"),
        (math.nan, "finite"),
    ],
)
def test_parse_length_rejects_everything_else(value, message):
    with pytest.raises(ConfigurationError, match=message):
        parse_length(value)


def test_nudge_defaults_to_zero_and_is_frozen():
    assert Nudge() == Nudge(0, 0)
    assert Nudge().is_zero
    assert not Nudge(0, 1).is_zero
    nudge = Nudge(1, -2)
    assert (nudge.dx, nudge.dy) == (1.0, -2.0)
    assert isinstance(nudge.dx, float)
    with pytest.raises(AttributeError):
        nudge.dx = 3  # type: ignore[misc]


@pytest.mark.parametrize("bad", [math.nan, math.inf, "1pt", True, None])
def test_nudge_rejects_non_numbers(bad):
    with pytest.raises(ConfigurationError):
        Nudge(bad, 0)
    with pytest.raises(ConfigurationError):
        Nudge(0, bad)


def test_nudge_from_combines_opposite_directions():
    assert nudge_from() == Nudge(0, 0)
    assert nudge_from(top="10pt") == Nudge(0, 10)
    assert nudge_from(bottom=4) == Nudge(0, -4)
    assert nudge_from(top="10pt", bottom="4pt") == Nudge(0, 6)
    assert nudge_from(right="6pt") == Nudge(6, 0)
    assert nudge_from(left="6pt") == Nudge(-6, 0)
    assert nudge_from(right=1, left=3) == Nudge(-2, 0)
    assert nudge_from(top="-2pt") == Nudge(0, -2)
    nudge = nudge_from(top="1em", left="0.5em", right="2mm", font_size=10)
    assert nudge.dy == pytest.approx(10)
    assert nudge.dx == pytest.approx(2 * MM - 5)


def test_nudge_from_needs_a_font_size_for_em_and_reports_bad_lengths():
    with pytest.raises(ConfigurationError, match="font size"):
        nudge_from(top="1em")
    with pytest.raises(ConfigurationError, match="Invalid length"):
        nudge_from(left="lots")


def _labels(nudge):
    return [
        PointLabelLayer((1, 2), "A", nudge=nudge),
        RegionLabelLayer("fill", "Region", nudge=nudge),
        TextLayer((1, 2), "T", nudge=nudge),
        SpanBraceLayer((0, 1), (2, 1), "Gap", nudge=nudge),
        BraceLayer("x", 0, 2, "Span", nudge=nudge),
    ]


def test_label_layers_carry_an_optional_nudge():
    for layer in _labels(None):
        assert layer.nudge is None
    for layer in _labels(Nudge(1, 2)):
        assert layer.nudge == Nudge(1, 2)
    assert PointLabelLayer((1, 2), "A").nudge is None


@pytest.mark.parametrize("bad", [(1, 2), "10pt", 3])
def test_label_layers_reject_a_nudge_that_is_not_a_nudge(bad):
    for factory in (
        lambda: PointLabelLayer((1, 2), "A", nudge=bad),
        lambda: RegionLabelLayer("fill", "Region", nudge=bad),
        lambda: TextLayer((1, 2), "T", nudge=bad),
        lambda: SpanBraceLayer((0, 1), (2, 1), "Gap", nudge=bad),
        lambda: BraceLayer("x", 0, 2, "Span", nudge=bad),
    ):
        with pytest.raises(ConfigurationError, match="nudge"):
            factory()


def test_text_layer_total_offset_adds_the_nudge_to_the_offset():
    assert TextLayer((0, 0), "T", offset=(3, 4)).total_offset == (3, 4)
    assert TextLayer((0, 0), "T", offset=(3, 4), nudge=Nudge(1, -6)).total_offset == (4, -2)


def test_documents_round_trip_a_nudge_and_omit_an_unset_one():
    scene = Scene(tuple(_labels(Nudge(1.5, -2))))
    document = scene_to_dict(scene)
    for layer in document["layers"]:
        assert layer["nudge"] == {"$": "Nudge", "dx": 1.5, "dy": -2.0}
    assert scene_from_dict(document) == scene

    unset = Scene(tuple(_labels(None)))
    plain = scene_to_dict(unset)
    assert all("nudge" not in layer for layer in plain["layers"])
    assert scene_from_dict(plain) == unset
