import pytest

import mosaickit
from mosaickit import ConfigurationError, RegionLabelLayer, Stroke


def test_region_label_defaults():
    layer = RegionLabelLayer("fill.dwl", "Deadweight loss")
    assert layer.region == "fill.dwl"
    assert layer.short_text is None
    assert layer.placement == "auto"
    assert layer.role == "text"
    assert layer.stroke == Stroke(width=0.8)


def test_region_label_accepts_a_polygon():
    layer = RegionLabelLayer([(0, 0), (1, 0), (0, 1)], "A")
    assert layer.region == ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RegionLabelLayer("", "A"),
        lambda: RegionLabelLayer([(0, 0), (1, 1)], "A"),
        lambda: RegionLabelLayer("r", ""),
        lambda: RegionLabelLayer("r", "A", short_text=""),
        lambda: RegionLabelLayer("r", "A", placement="outside"),
    ],
)
def test_region_label_rejects_invalid_values(factory):
    with pytest.raises(ConfigurationError):
        factory()


def test_layout_warning_is_exported():
    assert issubclass(mosaickit.LayoutWarning, UserWarning)
    assert {"LayoutWarning", "RegionLabelLayer"} <= set(mosaickit.__all__)
