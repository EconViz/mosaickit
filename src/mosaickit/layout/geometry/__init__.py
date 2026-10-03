"""Pure 2-D geometry in display pixels."""

from mosaickit.layout.geometry.polygon import (
    point_in_polygon,
    polygon_edges,
    ray_exit,
    rect_inside_polygon,
    rect_overlaps_polygon,
)
from mosaickit.layout.geometry.polylabel import polylabel
from mosaickit.layout.geometry.rect import Point, Polygon, Rect, Segment
from mosaickit.layout.geometry.segments import rect_hits_segment, segments_intersect

__all__ = [
    "Point",
    "Polygon",
    "Rect",
    "Segment",
    "point_in_polygon",
    "polygon_edges",
    "polylabel",
    "ray_exit",
    "rect_hits_segment",
    "rect_inside_polygon",
    "rect_overlaps_polygon",
    "segments_intersect",
]
