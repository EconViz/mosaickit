import json
from dataclasses import replace
from pathlib import Path

import pytest

from mosaickit import (
    ArrowLayer,
    AxisMarkLayer,
    AxisNoteLayer,
    BraceLayer,
    Canvas,
    ConfigurationError,
    Fill,
    FillLayer,
    GroupLayer,
    LegendLayer,
    MarkerLayer,
    Parameter,
    PathLayer,
    PointLabelLayer,
    RegionLabelLayer,
    Scene,
    SpanBraceLayer,
    Stroke,
    TextLayer,
    TextStyle,
    quadrant_axes,
)
from mosaickit.document import (
    MAX_DEPTH,
    MAX_NODES,
    MAX_STRING,
    VERSION,
    scene_from_dict,
    scene_from_json,
    scene_to_dict,
    scene_to_json,
)
from mosaickit.parameter.expression import Constant
from mosaickit.styles import ArrowPlacement, DashStyle, Marker


def _every_layer() -> Scene:
    shift = Parameter("shift", value_type=float)
    layers = [
        *quadrant_axes(10, 10),
        FillLayer([(1, 1), (1, 7), (8, 1)], fill=Fill(color="#377EB8", opacity=0.2), id="area"),
        PathLayer(
            [(1, 8), (2, 5), (4, 3)],
            stroke=Stroke(color="#984EA3", width=2, dash=DashStyle.DASHED),
            arrow_placement=ArrowPlacement.BOTH,
        ),
        PathLayer([(1, 1 + shift), (9, 4 + shift)], role="secondary"),
        MarkerLayer([(4, 3), (5, shift * 2 + 1)], marker=Marker(size=40, shape="s")),
        TextLayer((4, 3), "A", offset=(6, 6), anchor="top-right", style=TextStyle(size=11)),
        TextLayer((1, 1), "$x_1$", math=True),
        ArrowLayer((1, 1), (3, 3), label="move"),
        AxisMarkLayer("y", 7, "a_1", math=True),
        AxisNoteLayer("y", 5, "Lower\nvalue"),
        BraceLayer("y", 5, 7, "Span", side="outside"),
        SpanBraceLayer((3, 2.7), (3, 5), "gap", side="left"),
        PointLabelLayer((4, 3), "P"),
        RegionLabelLayer("area", "Feasible", short_text="F"),
        LegendLayer(("a", "b")),
        GroupLayer((TextLayer((2, 2), "in group"),)),
    ]
    return Scene(layers, {"title": "Every layer"})


def test_every_public_layer_type_round_trips():
    scene = _every_layer()
    assert scene_from_dict(scene_to_dict(scene)) == scene
    assert scene_from_json(scene_to_json(scene)) == scene


def test_the_document_is_plain_json():
    document = scene_to_dict(_every_layer())
    assert json.loads(json.dumps(document, allow_nan=False)) == document
    assert document["format"] == "mosaickit.scene"
    assert document["version"] == VERSION


def test_a_bound_scene_serializes_like_the_bound_canvas():
    shift = Parameter("shift", value_type=float)
    template = Canvas().add(PathLayer([(1, 1 + shift), (9, 4 + shift)], id="line"))
    bound = template.bind(shift, 2.0)
    document = scene_to_dict(bound.snapshot())
    path = document["layers"][0]["path"]
    assert path[0][1] == 3.0  # the parameter is resolved in the bound snapshot
    assert "Parameter" not in json.dumps(document)
    assert scene_from_dict(document) == bound.snapshot()


def test_parameters_and_expressions_are_kept_in_an_unbound_scene():
    shift = Parameter("shift", value_type=float)
    scene = Scene([PathLayer([(0, shift + 1), (1, Constant(2.0))], id="p")])
    restored = scene_from_json(scene_to_json(scene))
    assert restored == scene
    assert restored.layers[0].path[0][1].free_parameters() == frozenset({shift})


def test_layer_ids_and_order_survive():
    scene = Scene([TextLayer((1, 1), "b", id="b"), TextLayer((2, 2), "a", id="a", z_index=-1)])
    restored = scene_from_dict(scene_to_dict(scene))
    assert [layer.id for layer in restored.layers] == ["b", "a"]
    assert [layer.z_index for layer in restored.layers] == [0, -1]


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda d: d.update(version=2), "version 2 is not supported"),
        (lambda d: d.update(version=True), "not supported"),
        (lambda d: d.update(format="other"), "format must be"),
        (lambda d: d.update(extra=1), "unknown keys"),
        (lambda d: d.update(layers="x"), "must be a list"),
        (lambda d: d.update(metadata={"a": 1}), "text to text"),
        (lambda d: d["layers"].append({"$": "Nope"}), "unknown kind 'Nope'"),
        (lambda d: d["layers"].append({"x": 1}), "needs a"),
        (lambda d: d["layers"].append("text"), r"layers\[1\].*is not a layer"),
        (lambda d: d["layers"].append(dict(d["layers"][0])), "Duplicate layer id"),
        (lambda d: d["layers"].append({"$": "TextLayer", "bogus": 1}), "no fields"),
        (lambda d: d["layers"].append({"$": "TextLayer"}), "TextLayer"),
        (lambda d: d["layers"].append({"$": "ArrowPlacement", "value": "sideways"}), "not a"),
        (
            lambda d: d["layers"].append({"$": "Parameter", "name": "x", "value_type": "complex"}),
            "unknown parameter type",
        ),
        (
            lambda d: d["layers"].append(
                {"$": "BinOp", "operation": "exec", "left": 1, "right": 2}
            ),
            "unknown operation",
        ),
        (lambda d: d["layers"].append({"$": "Color", "channels": [1, 1, 1]}), "four numbers"),
    ],
)
def test_loading_is_strict(mutate, message):
    document = scene_to_dict(Scene([TextLayer((1, 1), "ok", id="t")]))
    mutate(document)
    with pytest.raises(ConfigurationError, match=message):
        scene_from_dict(document)


def test_invalid_layer_values_report_their_path():
    document = scene_to_dict(Scene([TextLayer((1, 1), "ok", id="t")]))
    document["layers"][0]["anchor"] = "middle"
    with pytest.raises(ConfigurationError, match=r"layers\[0\].*anchor"):
        scene_from_dict(document)


def test_non_finite_numbers_are_rejected_both_ways():
    document = scene_to_dict(Scene([TextLayer((1, 1), "ok", id="t")]))
    document["layers"][0]["z_index"] = float("inf")
    with pytest.raises(ConfigurationError, match="finite"):
        scene_from_dict(document)
    with pytest.raises(ConfigurationError, match="finite"):
        scene_from_json('{"format": "mosaickit.scene", "version": 1, "layers": [NaN]}')
    with pytest.raises(ConfigurationError, match="not valid JSON"):
        scene_from_json("{")


def test_the_limits_stop_oversized_and_deeply_nested_documents():
    deep = {"$": "Constant", "value": 1}
    for _ in range(MAX_DEPTH + 2):
        deep = {"$": "Constant", "value": deep}
    document = {"format": "mosaickit.scene", "version": 1, "layers": [deep]}
    with pytest.raises(ConfigurationError, match="nested more than"):
        scene_from_dict(document)
    wide = {"format": "mosaickit.scene", "version": 1, "layers": [[0] * (MAX_NODES + 1)]}
    with pytest.raises(ConfigurationError, match="more than"):
        scene_from_dict(wide)
    long_text = scene_to_dict(Scene([TextLayer((1, 1), "ok", id="t")]))
    long_text["layers"][0]["text"] = "x" * (MAX_STRING + 1)
    with pytest.raises(ConfigurationError, match="longer than"):
        scene_from_dict(long_text)
    with pytest.raises(ConfigurationError, match="longer than"):
        scene_to_dict(Scene([TextLayer((1, 1), "x" * (MAX_STRING + 1))]))


def test_a_layer_with_an_object_geometry_says_what_it_cannot_serialize():
    class Curve:
        pass

    layer = PathLayer([(0, 0), (1, 1)], id="p")
    object.__setattr__(layer, "path", Curve())
    with pytest.raises(ConfigurationError, match=r"layers\[0\].path.*Curve"):
        scene_to_dict(Scene([layer]))


FIXTURE = Path(__file__).parent / "fixtures" / "scene_v1.json"


def _stable(layers, prefix="layer"):
    """The same layers with ids that do not change from run to run."""
    out = []
    for i, layer in enumerate(layers):
        name = layer.id if layer.id.startswith("axes.") or layer.id == "area" else f"{prefix}{i}"
        changes = {"id": name}
        if isinstance(layer, GroupLayer):
            changes["children"] = tuple(_stable(layer.children, f"{name}."))
        out.append(replace(layer, **changes))
    return out


def test_version_1_fixture_still_loads_and_still_matches():
    """Version 1 is frozen: this file is what a 1.x release must keep reading and writing.

    To start version 2, add scene_v2.json beside it and keep this test; do not edit this file.
    """
    scene = Scene(_stable(_every_layer().layers), {"title": "Every layer"})
    document = json.loads(FIXTURE.read_text())
    assert scene_to_dict(scene) == document
    assert scene_from_dict(document) == scene
