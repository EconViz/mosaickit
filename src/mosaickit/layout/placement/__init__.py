"""Decide where labels go: region labels inside or as callouts, point labels beside the point."""

from mosaickit.layout.placement.callout import place_callout
from mosaickit.layout.placement.inside import fits_inside
from mosaickit.layout.placement.obstacles import Obstacles, Placement
from mosaickit.layout.placement.point import place_point_label

__all__ = ["Obstacles", "Placement", "fits_inside", "place_callout", "place_point_label"]
