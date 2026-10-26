from mosaickit.diagram import estimate_text_size
from mosaickit.rendering.matplotlib import text_measurer


def test_measured_extents_scale_with_the_size_and_are_deterministic() -> None:
    small, large = text_measurer(10), text_measurer(20)
    assert small("LM") == text_measurer(10)("LM")
    assert large("LM")[0] > small("LM")[0] * 1.9
    assert all(isinstance(v, float) for v in small("W$_0$"))


def test_measured_extents_differ_from_the_estimate() -> None:
    label = r"$LM\,\left(\frac{M_0}{p_0}\right)$"
    measured = text_measurer(12)(label)
    estimated = estimate_text_size(label, 12, char_width=0.8, line_height=1.25)
    assert measured[0] > 0 and measured[1] > 0
    assert measured != estimated
