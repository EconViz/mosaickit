from dataclasses import FrozenInstanceError

import pytest
from bezierkit import CubicBezierSegment, Point
from bezierkit.core.geometry.point_set import PointSet

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


def test_geometry_is_copied_and_native_segments_preserved():
    points = PointSet([(0, 0), (1, 1)])
    layer = PathLayer(points)
    assert layer.path == (Point(0, 0), Point(1, 1))
    with pytest.raises(FrozenInstanceError):
        layer.visible = False
    segment = CubicBezierSegment.from_line(Point(0, 0), Point(1, 1))
    assert PathLayer(segment).path is segment


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PathLayer([]),
        lambda: MarkerLayer([]),
        lambda: PathLayer([(0, 0, 0), (1, 1, 1)]),
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
