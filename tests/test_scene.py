from dataclasses import FrozenInstanceError

import pytest

from mosaickit import (
    ArrowPlacement,
    AxisSpec,
    ConfigurationError,
    GroupLayer,
    MarkerLayer,
    PathLayer,
    Scene,
    TextLayer,
    box_frame,
    build_axes,
    crosshair_axes,
    quadrant_axes,
)


def test_scene_persistence_order_and_nested_removal():
    a = PathLayer([(0, 0), (1, 1)], id="a", z_index=2)
    b = TextLayer((1, 1), "b", id="b", z_index=1)
    c = TextLayer((2, 2), "c", id="c", z_index=1)
    empty = Scene.empty()
    scene = empty.extend([a, b, c])
    assert empty.layers == ()
    assert tuple(layer.id for layer in scene.ordered_layers) == ("b", "c", "a")
    assert scene.remove("b").layers == (a, c)
    assert scene.clear().layers == ()
    nested = Scene((GroupLayer((a,), id="group"),))
    assert nested.remove("a").layers[0].children == ()
    with pytest.raises(ConfigurationError, match="Unknown"):
        scene.remove("missing")


def test_duplicate_ids_include_hidden_nested_layers():
    a = TextLayer((0, 0), "a", id="same")
    with pytest.raises(ConfigurationError, match="same"):
        Scene((a, GroupLayer((a,), visible=False)))


def test_geometry_is_copied_and_normalized_to_coordinate_tuples():
    points = [[0, 0], [1, 1]]
    layer = PathLayer(points)
    assert layer.path == ((0.0, 0.0), (1.0, 1.0))
    points[0][0] = 9
    assert layer.path == ((0.0, 0.0), (1.0, 1.0))
    with pytest.raises(FrozenInstanceError):
        layer.visible = False


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PathLayer([]),
        lambda: MarkerLayer([]),
        lambda: PathLayer([(0, 0, 0), (1, 1, 1)]),
        lambda: PathLayer([(0, 0), (float("nan"), 1)]),
        lambda: MarkerLayer([(0, float("inf"))]),
        lambda: TextLayer(("x", 0), "bad"),
        lambda: TextLayer((0, 0, 0), "bad"),
        lambda: TextLayer((0, 0), "bad", role="a..b"),
        lambda: TextLayer((0, 0), "bad", z_index=float("nan")),
        lambda: TextLayer((0, 0), "bad", offset=(0, float("inf"))),
        lambda: AxisSpec((1, 0)),
    ],
)
def test_invalid_layers(factory):
    with pytest.raises(ConfigurationError):
        factory()


def test_axis_presets_are_the_generic_assembler():
    assert quadrant_axes(5, 6) == build_axes(
        AxisSpec((0, 5), ArrowPlacement.END), AxisSpec((0, 6), ArrowPlacement.END)
    )
    assert crosshair_axes((-2, 3), (-4, 5)) == build_axes(
        AxisSpec((-2, 3), ArrowPlacement.BOTH), AxisSpec((-4, 5), ArrowPlacement.BOTH)
    )
    frame = box_frame(5, 6)
    assert frame == build_axes(AxisSpec((0, 5)), AxisSpec((0, 6)))
    assert len(frame[0].path) == 5
    assert frame[0].path[0] == frame[0].path[-1]


@pytest.mark.parametrize(
    "anchor,expected",
    [
        ("center", ("center", "center")),
        ("left", ("left", "center")),
        ("right", ("right", "center")),
        ("top", ("center", "top")),
        ("bottom", ("center", "bottom")),
        ("top-left", ("left", "top")),
        ("top-right", ("right", "top")),
        ("bottom-left", ("left", "bottom")),
        ("bottom-right", ("right", "bottom")),
    ],
)
def test_text_anchor_table(anchor, expected):
    from mosaickit.scene.text import TEXT_ANCHORS

    assert TextLayer((0, 0), "x", anchor=anchor).anchor == anchor
    assert TEXT_ANCHORS[anchor] == expected


@pytest.mark.parametrize("anchor", ["upper left", "left-top", "middle", ""])
def test_text_anchor_rejects_unknown_values(anchor):
    with pytest.raises(ConfigurationError, match="Unsupported text anchor"):
        TextLayer((0, 0), "x", anchor=anchor)
