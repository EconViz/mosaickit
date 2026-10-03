"""Decide where labels go: inside a region, out as a callout, beside a point, or beside an anchor."""

from mosaickit.layout.placement.beside import place_beside
from mosaickit.layout.placement.callout import place_callout
from mosaickit.layout.placement.inside import fits_inside
from mosaickit.layout.placement.obstacles import Obstacles, Placement
from mosaickit.layout.placement.point import place_point_label

__all__ = [
    "Obstacles",
    "Placement",
    "fits_inside",
    "place_beside",
    "place_callout",
    "place_point_label",
]
