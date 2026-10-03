"""Domain-neutral label layout in display coordinates."""

from mosaickit.layout.geometry import Rect, polylabel
from mosaickit.layout.placement import (
    Obstacles,
    Placement,
    fits_inside,
    place_callout,
    place_point_label,
)

__all__ = [
    "Obstacles",
    "Placement",
    "Rect",
    "fits_inside",
    "place_callout",
    "place_point_label",
    "polylabel",
]
