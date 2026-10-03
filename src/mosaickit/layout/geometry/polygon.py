"""Polygon containment, overlap, and ray tests."""

from mosaickit.layout.geometry.rect import Point, Polygon, Rect, Segment
from mosaickit.layout.geometry.segments import rect_hits_segment


def polygon_edges(polygon: Polygon) -> tuple[Segment, ...]:
    points = tuple(polygon)
    return tuple((points[i], points[(i + 1) % len(points)]) for i in range(len(points)))


def point_in_polygon(point: Point, polygon: Polygon) -> bool:
    x, y = point
    inside = False
    for (x0, y0), (x1, y1) in polygon_edges(polygon):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def rect_inside_polygon(rect: Rect, polygon: Polygon) -> bool:
    if not all(point_in_polygon(corner, polygon) for corner in rect.corners()):
        return False
    return not any(rect_hits_segment(rect, a, b) for a, b in polygon_edges(polygon))


def rect_overlaps_polygon(rect: Rect, polygon: Polygon) -> bool:
    if any(point_in_polygon(corner, polygon) for corner in rect.corners()):
        return True
    # Also catches a polygon lying entirely inside the rect: its edges' endpoints are inside.
    return any(rect_hits_segment(rect, a, b) for a, b in polygon_edges(polygon))


def ray_exit(origin: Point, direction: Point, polygon: Polygon) -> float:
    """Distance along unit ``direction`` to the farthest polygon edge hit, or 0."""
    ox, oy = origin
    rx, ry = direction
    farthest = 0.0
    for (ax, ay), (bx, by) in polygon_edges(polygon):
        sx, sy = bx - ax, by - ay
        denom = rx * sy - ry * sx
        if denom == 0:
            continue
        qx, qy = ax - ox, ay - oy
        t = (qx * sy - qy * sx) / denom
        u = (qx * ry - qy * rx) / denom
        if t >= 0 and 0 <= u <= 1:
            farthest = max(farthest, t)
    return farthest
