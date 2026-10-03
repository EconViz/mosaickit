import pytest

import mosaickit
import mosaickit.scene
from mosaickit import ConfigurationError, PointLabelLayer, TextStyle


def test_point_label_defaults():
    layer = PointLabelLayer((1, 2), "Dot")
    assert layer.point == (1.0, 2.0)
    assert layer.text == "Dot"
    assert layer.style is None
    assert layer.role == "text"
    assert layer.fallback_category == "text"


def test_point_label_declares_its_text_style_slot():
    assert PointLabelLayer.style_slots == {"text": "style"}
    layer = PointLabelLayer((0, 0), "A", style=TextStyle(size=9))
    assert layer.style == TextStyle(size=9)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PointLabelLayer((0, 0), ""),
        lambda: PointLabelLayer((0, 0), 3),
        lambda: PointLabelLayer((0,), "A"),
        lambda: PointLabelLayer((0, float("nan")), "A"),
    ],
)
def test_point_label_rejects_invalid_values(factory):
    with pytest.raises(ConfigurationError):
        factory()


def test_point_label_is_exported():
    assert "PointLabelLayer" in mosaickit.__all__
    assert "PointLabelLayer" in mosaickit.scene.__all__
    assert mosaickit.scene.PointLabelLayer is PointLabelLayer
