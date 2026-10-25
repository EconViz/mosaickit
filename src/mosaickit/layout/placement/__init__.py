"""Decide where labels go: in a region, as a callout, beside a point, or beside an anchor."""

from mosaickit.layout.placement.beside import place_beside
from mosaickit.layout.placement.callout import follow_leader, place_callout
from mosaickit.layout.placement.inside import fits_inside
from mosaickit.layout.placement.leader import leader_anchor
from mosaickit.layout.placement.obstacles import Obstacles, Placement
from mosaickit.layout.placement.point import place_point_label
from mosaickit.layout.placement.rotation import (
    RotationPlacement,
    extend_polyline_tail,
    place_rotation_marker,
    tail_label_position,
)

__all__ = [
    "Obstacles",
    "Placement",
    "RotationPlacement",
    "extend_polyline_tail",
    "fits_inside",
    "follow_leader",
    "leader_anchor",
    "place_beside",
    "place_callout",
    "place_point_label",
    "place_rotation_marker",
    "tail_label_position",
]
