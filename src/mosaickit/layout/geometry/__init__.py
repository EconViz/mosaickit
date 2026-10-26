"""Pure 2-D geometry in any consistent Cartesian coordinate system."""

from mosaickit.layout.geometry.brace import Brace, brace_outline
from mosaickit.layout.geometry.lines import (
    Polyline,
    View,
    axis_span_for_display_slope,
    centered_view,
    chord_to_rect,
    clip_polyline,
    clip_polyline_fragments,
    clip_segment,
    data_slope_for_display,
    display_slope,
    extend_chord,
    extend_line_through,
    line_through_display_angle,
    line_through_display_slope,
)
from mosaickit.layout.geometry.polygon import (
    distance_to_boundary,
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
    "Brace",
    "Point",
    "Polygon",
    "Polyline",
    "View",
    "axis_span_for_display_slope",
    "centered_view",
    "clip_polyline_fragments",
    "data_slope_for_display",
    "display_slope",
    "extend_line_through",
    "Rect",
    "Segment",
    "brace_outline",
    "chord_to_rect",
    "clip_polyline",
    "clip_segment",
    "distance_to_boundary",
    "extend_chord",
    "line_through_display_angle",
    "line_through_display_slope",
    "point_in_polygon",
    "polygon_edges",
    "polylabel",
    "ray_exit",
    "rect_hits_segment",
    "rect_inside_polygon",
    "rect_overlaps_polygon",
    "segments_intersect",
]
