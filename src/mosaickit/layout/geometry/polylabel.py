"""Pole of inaccessibility: the interior point farthest from the boundary.

For a triangle this is the incenter. It suits thin regions better than the
centroid. Best-first search over square cells (Mapbox polylabel).
"""

import heapq
import math

from mosaickit.layout.geometry.polygon import distance_to_boundary, point_in_polygon
from mosaickit.layout.geometry.rect import Point, Polygon

_Cell = tuple[float, float, float, float, float]  # (-max possible, distance, x, y, half size)


def _signed_distance(point: Point, polygon: Polygon) -> float:
    distance = distance_to_boundary(point, polygon)
    return distance if point_in_polygon(point, polygon) else -distance


def _cell(x: float, y: float, half: float, polygon: Polygon) -> _Cell:
    distance = _signed_distance((x, y), polygon)
    return (-(distance + half * math.sqrt(2)), distance, x, y, half)


def polylabel(polygon: Polygon, precision: float = 1.0) -> Point:
    points = tuple(polygon)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, min_y, max_x, max_y = min(xs), min(ys), max(xs), max(ys)
    size = min(max_x - min_x, max_y - min_y)
    if size == 0:
        return (float(points[0][0]), float(points[0][1]))

    heap: list[_Cell] = []
    x = min_x
    while x < max_x:
        y = min_y
        while y < max_y:
            heapq.heappush(heap, _cell(x + size / 2, y + size / 2, size / 2, points))
            y += size
        x += size

    center = _cell((min_x + max_x) / 2, (min_y + max_y) / 2, 0, points)
    best_distance, best = center[1], (center[2], center[3])
    while heap:
        negative_max, distance, cx, cy, half = heapq.heappop(heap)
        if distance > best_distance:
            best_distance, best = distance, (cx, cy)
        if -negative_max - best_distance <= precision:
            continue
        half /= 2
        for sx in (-half, half):
            for sy in (-half, half):
                heapq.heappush(heap, _cell(cx + sx, cy + sy, half, points))
    return best
