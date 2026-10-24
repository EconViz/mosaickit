"""Callout leaders end at one of the label box's eight anchors, picked by where the start lies."""

import io
import math
import warnings
import xml.etree.ElementTree as ET

import pytest

from mosaickit import (
    Canvas,
    Fill,
    FillLayer,
    LayoutWarning,
    Nudge,
    RegionLabelLayer,
)
from mosaickit.layout import Rect, leader_anchor

PAD_PT = 2.0  # the callout box is the text plus this much on every side
GAP_PT = 2.0  # the leader stops this far short of its anchor
CENTER = (4.0, 4.0)
# anchor number -> (sx, sy) with y up:  1 2 3 / 4 . 5 / 6 7 8
STEPS = {
    1: (-1, 1),
    2: (0, 1),
    3: (1, 1),
    4: (-1, 0),
    5: (1, 0),
    6: (-1, -1),
    7: (0, -1),
    8: (1, -1),
}
# the direction (degrees, from the label box centre) the start lies in, per anchor number
FACING = {5: 0, 3: 45, 2: 90, 1: 135, 4: 180, 6: 225, 7: 270, 8: 315}


def _scene(nudge=None):
    return [
        FillLayer([(4, 4), (4.3, 4), (4, 4.3)], fill=Fill(opacity=0.2), id="tiny"),
        RegionLabelLayer(
            "tiny", "Consumer surplus", id="tiny.label", placement="callout", nudge=nudge
        ),
    ]


def _render(nudge=None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", LayoutWarning)
        return Canvas().extend(_scene(nudge)).render()


def _measure(result):
    """The label box (text plus padding), the leader's two ends, in display pixels."""
    ax = result.axes
    scale = ax.figure.dpi / 72
    (text,) = [t for t in ax.texts if t.get_gid() == "tiny.label"]
    (line,) = [ln for ln in ax.lines if ln.get_gid() == "tiny.label.leader"]
    box = text.get_window_extent(ax.figure.canvas.get_renderer())
    rect = Rect(box.x0, box.y0, box.x1, box.y1).inflate(PAD_PT * scale)
    start, end = (tuple(ax.transData.transform(p)) for p in line.get_xydata())
    return rect, start, end, scale


def _number(rect, point):
    """Which of the eight anchors of ``rect`` is ``point`` (to within a pixel), or None."""
    cx, cy = rect.center
    for number, (sx, sy) in STEPS.items():
        if math.dist(point, (cx + sx * rect.width / 2, cy + sy * rect.height / 2)) < 1.0:
            return number
    return None


def _facing(rect, start):
    """The anchor number the octant of ``start`` (by plain angle) calls for."""
    cx, cy = rect.center
    angle = math.degrees(math.atan2(start[1] - cy, start[0] - cx)) % 360
    return min(FACING, key=lambda n: min(abs(angle - FACING[n]), 360 - abs(angle - FACING[n])))


def _assert_ends_at_anchor(rect, start, end, scale, number):
    anchor = leader_anchor(start, rect)
    assert _number(rect, anchor) == number
    assert math.dist(end, anchor) == pytest.approx(GAP_PT * scale, abs=1e-6)
    # ...on the straight line from the start to that anchor
    along = math.dist(start, end) + math.dist(end, anchor)
    assert along == pytest.approx(math.dist(start, anchor), abs=1e-6)


def test_an_untouched_callout_ends_at_an_anchor():
    result = _render()
    try:
        rect, start, end, scale = _measure(result)
    finally:
        result.close()
    _assert_ends_at_anchor(rect, start, end, scale, _facing(rect, start))
    assert not rect.contains(start)


@pytest.mark.parametrize("number", sorted(FACING))
def test_a_label_moved_to_each_direction_gets_the_matching_anchor(number):
    base = _render()
    try:
        rect0, start0, _, scale = _measure(base)
    finally:
        base.close()
    # put the label centre 90 pt from the start, on the side opposite the direction FACING[number]
    angle = math.radians(FACING[number])
    target = (start0[0] - 90 * scale * math.cos(angle), start0[1] - 90 * scale * math.sin(angle))
    nudge = Nudge((target[0] - rect0.center[0]) / scale, (target[1] - rect0.center[1]) / scale)
    moved = _render(nudge)
    try:
        rect, start, end, scale = _measure(moved)
    finally:
        moved.close()
    assert start == pytest.approx(start0)  # still leaves the region at the same spot
    assert _facing(rect, start) == number
    _assert_ends_at_anchor(rect, start, end, scale, number)


def test_all_eight_anchors_are_reachable_by_nudging():
    seen = set()
    base = _render()
    try:
        rect0, start0, _, scale = _measure(base)
    finally:
        base.close()
    for degrees in FACING.values():
        angle = math.radians(degrees)
        target = (
            start0[0] - 90 * scale * math.cos(angle),
            start0[1] - 90 * scale * math.sin(angle),
        )
        moved = _render(
            Nudge((target[0] - rect0.center[0]) / scale, (target[1] - rect0.center[1]) / scale)
        )
        try:
            rect, start, _, _ = _measure(moved)
        finally:
            moved.close()
        seen.add(_number(rect, leader_anchor(start, rect)))
    assert seen == set(STEPS)


def test_nudging_the_label_from_beside_the_start_to_above_it_re_anchors_the_leader():
    base = _render()
    try:
        rect0, start0, end0, scale = _measure(base)
    finally:
        base.close()
    number0 = _number(rect0, leader_anchor(start0, rect0))
    assert number0 is not None
    # straight above the start, well clear of it
    dx = (start0[0] - rect0.center[0]) / scale
    dy = (start0[1] + 80 * scale + rect0.height / 2 - rect0.center[1]) / scale
    moved = _render(Nudge(dx, dy))
    try:
        rect, start, end, scale = _measure(moved)
    finally:
        moved.close()
    assert _number(rect, leader_anchor(start, rect)) == 7  # bottom edge midpoint
    assert number0 != 7
    _assert_ends_at_anchor(rect, start, end, scale, 7)
    assert end[0] == pytest.approx(rect.center[0], abs=1e-6)  # straight up to the midpoint


def test_the_svg_leader_is_one_straight_segment():
    buffer = io.BytesIO()
    _render_canvas = Canvas().extend(_scene(Nudge(30, -40)))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", LayoutWarning)
        result = _render_canvas.render()
    try:
        result.figure.savefig(buffer, format="svg")
    finally:
        result.close()
    root = ET.fromstring(buffer.getvalue())
    (group,) = [e for e in root.iter() if e.get("id") == "tiny.label.leader"]
    paths = [e for e in group.iter() if e.tag.endswith("}path")]
    assert len(paths) == 1
    assert paths[0].get("d", "").count("M") == 1
    assert paths[0].get("d", "").count("L") == 1  # M start L end: nothing but a straight segment
