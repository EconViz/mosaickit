"""Domain-neutral label layout in display coordinates."""

from mosaickit.layout.geometry import Rect, polylabel
from mosaickit.layout.placement import (
    Obstacles,
    Placement,
    RotationPlacement,
    extend_polyline_tail,
    fits_inside,
    follow_leader,
    leader_anchor,
    place_callout,
    place_point_label,
    place_rotation_marker,
    tail_label_position,
)

__all__ = [
    "Obstacles",
    "Placement",
    "RotationPlacement",
    "Rect",
    "extend_polyline_tail",
    "fits_inside",
    "follow_leader",
    "leader_anchor",
    "place_callout",
    "place_point_label",
    "place_rotation_marker",
    "polylabel",
    "tail_label_position",
]
