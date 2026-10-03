"""Pure 2-D geometry in display pixels."""

from mosaickit.layout.geometry.rect import Point, Polygon, Rect, Segment
from mosaickit.layout.geometry.segments import rect_hits_segment, segments_intersect

__all__ = [
    "Point",
    "Polygon",
    "Rect",
    "Segment",
    "rect_hits_segment",
    "segments_intersect",
]
