"""One global label placer for curve names, point labels and tick labels.

Pure geometry in display units: see :func:`place_labels`.
"""

from mosaickit.layout.labels.model import (
    Label,
    Obstacle,
    Placement,
    PlacementResult,
    PlacementWarning,
)
from mosaickit.layout.labels.options import COMPASS, TICK_STRATEGIES, LabelOptions
from mosaickit.layout.labels.place import place_labels

__all__ = [
    "COMPASS",
    "TICK_STRATEGIES",
    "Label",
    "LabelOptions",
    "Obstacle",
    "Placement",
    "PlacementResult",
    "PlacementWarning",
    "place_labels",
]
