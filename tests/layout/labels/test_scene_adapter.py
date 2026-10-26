"""The one-call adapter: layers in, replacement text layers (and leaders) out."""

from __future__ import annotations

import pytest
from scenes import CANVAS

from mosaickit.label_scene import SceneLabelOptions, curve_end, place_scene_labels
from mosaickit.layout import Rect
from mosaickit.layout.labels import LabelOptions
from mosaickit.scene import ArrowLayer, MarkerLayer, PathLayer, TextLayer
from mosaickit.styles import TextStyle


def measure(text: str) -> tuple[float, float]:
    return (7.0 * len(text), 14.0)


def figure():
    layers = []
    names = []
    for i in range(3):
        end = (300.0 + 14 * i, 230.0 - 6 * i)
        path = PathLayer([(40.0 + 42 * i, 30.0), end], id=f"p{i}", role="macro.curve")
        layers += [path, TextLayer(end, f"LM{i}", id=f"p{i}.label", style=TextStyle(size=12))]
        names.append(layers[-1])
    layers.append(MarkerLayer([(100.0, 100.0)], id="m"))
    layers.append(ArrowLayer((10.0, 10.0), (10.0, 270.0), id="axis"))
    return layers, names


def test_names_keep_their_anchor_style_and_get_an_offset() -> None:
    layers, names = figure()
    owners = {f"p{i}.label": f"p{i}" for i in range(3)}  # explicit, never parsed from ids
    out, result = place_scene_labels(layers, names, CANVAS, (1.0, 1.0), measure, owners=owners)
    texts = {layer.id: layer for layer in out if isinstance(layer, TextLayer)}
    assert set(texts) == {n.id for n in names}
    for name in names:
        placed = texts[name.id]
        assert placed.position == name.position  # the anchor is the label's own
        assert placed.style == name.style  # the font size is never touched
        assert placed.text == name.text
    assert result.ok


def test_leaders_are_layers_with_the_configured_role() -> None:
    layers, names = figure()
    options = SceneLabelOptions(
        leader_role="macro.leader", placement=LabelOptions(leader_after=2.0)
    )
    out, _ = place_scene_labels(layers, names, CANVAS, (1.0, 1.0), measure, options)
    leaders = [layer for layer in out if isinstance(layer, PathLayer)]
    assert leaders and all(layer.role == "macro.leader" for layer in leaders)
    assert all(layer.id.endswith(".leader") for layer in leaders)


def test_data_units_are_scaled_to_points_and_back() -> None:
    layers = [PathLayer([(0.0, 0.0), (10.0, 5.0)], id="c")]
    name = TextLayer((10.0, 5.0), "c", id="c.label")
    out, result = place_scene_labels(
        layers, [name], Rect(0.0, 0.0, 400.0, 300.0), (30.0, 40.0), measure
    )
    assert result.ok
    placed = out[0]
    assert placed.position == (10.0, 5.0)
    assert abs(placed.offset[0]) <= 60 and abs(placed.offset[1]) <= 60


def test_ticks_and_fixed_texts_share_the_scene() -> None:
    layers = [
        PathLayer([(0.0, 100.0), (360.0, 100.0)], id="axis"),
        TextLayer((100.0, 100.0), "title", id="title", anchor="bottom"),
    ]
    ticks = [
        TextLayer((100.0, 100.0), "W0", id="t0"),
        TextLayer((104.0, 100.0), "W1", id="t1"),
    ]
    out, result = place_scene_labels(layers, [], CANVAS, (1.0, 1.0), measure, ticks=ticks)
    assert result.ok
    placed = {layer.id: layer for layer in out}
    assert placed["t0"].offset != placed["t1"].offset


def test_non_numeric_geometry_is_ignored() -> None:
    from mosaickit.parameter import Parameter

    k = Parameter("k", 1.0)
    layers = [PathLayer([(0.0, 0.0), (k, 5.0)], id="live")]
    name = TextLayer((10.0, 5.0), "n", id="n")
    _, result = place_scene_labels(layers, [name], CANVAS, (1.0, 1.0), measure)
    assert result.ok


@pytest.mark.parametrize(
    ("policy", "expected"),
    [("rightmost", (5.0, 1.0)), ("last", (2.0, 9.0)), ("first", (0.0, 0.0)), ("top", (2.0, 9.0))],
)
def test_curve_end_policies(policy: str, expected: tuple[float, float]) -> None:
    path = [(0.0, 0.0), (5.0, 1.0), (2.0, 9.0)]
    assert curve_end(path, policy) == expected  # type: ignore[arg-type]
