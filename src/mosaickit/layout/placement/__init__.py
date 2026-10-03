"""Decide where a region label goes: inside the region, or out as a callout."""

from mosaickit.layout.placement.callout import place_callout
from mosaickit.layout.placement.inside import fits_inside
from mosaickit.layout.placement.obstacles import Obstacles, Placement

__all__ = ["Obstacles", "Placement", "fits_inside", "place_callout"]
