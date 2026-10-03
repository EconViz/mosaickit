"""Domain-neutral label layout in display coordinates."""

from mosaickit.layout.geometry import Rect, polylabel
from mosaickit.layout.placement import Obstacles, Placement, fits_inside, place_callout

__all__ = ["Obstacles", "Placement", "Rect", "fits_inside", "place_callout", "polylabel"]
