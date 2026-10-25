"""Place curved rotation markers between two paths in display coordinates."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from mosaickit.layout.geometry import (
    Point,
    Rect,
    Segment,
    point_in_polygon,
    polygon_edges,
    rect_hits_segment,
    segments_intersect,
)
from mosaickit.layout.placement.obstacles import Obstacles

Polyline = tuple[Point, ...]
Connector = Callable[[Point, Point, Point], Sequence[Point]]
_NO_OBSTACLES = Obstacles()


@dataclass(frozen=True, slots=True)
class RotationPlacement:
    """A collision-free connector selected at one radial search position."""

    path: Polyline
    start: Point
    end: Point
    radius: float
    fraction: float


def _sub(first: Point, second: Point) -> Point:
    return first[0] - second[0], first[1] - second[1]


def _add(first: Point, second: Point) -> Point:
    return first[0] + second[0], first[1] + second[1]


def _scale(point: Point, factor: float) -> Point:
    return point[0] * factor, point[1] * factor


def _dot(first: Point, second: Point) -> float:
    return first[0] * second[0] + first[1] * second[1]


def _norm(point: Point) -> float:
    return math.hypot(*point)


def _unit(point: Point) -> Point:
    length = _norm(point)
    if length == 0:
        raise ValueError("direction must have non-zero length")
    return point[0] / length, point[1] / length


def _nearest_on_segment(point: Point, start: Point, end: Point) -> tuple[Point, float]:
    direction = _sub(end, start)
    denominator = _dot(direction, direction)
    share = 0.0 if denominator == 0 else _dot(_sub(point, start), direction) / denominator
    share = min(1.0, max(0.0, share))
    return _add(start, _scale(direction, share)), share


def _branch(path: Polyline, pivot: Point, preferred: Point | None = None) -> Polyline:
    choices = []
    for index in (0, -1):
        direction = _sub(path[index], pivot)
        distance = _norm(direction)
        aligned = preferred is None or (
            distance > 0 and _dot(_scale(direction, 1 / distance), preferred) > 0
        )
        choices.append((aligned, distance, index))
    aligned_choices = [choice for choice in choices if choice[0]] or choices
    _, _, tail_index = max(aligned_choices, key=lambda choice: choice[1])

    closest_point = path[0]
    closest_segment = 0
    closest_distance = math.inf
    for index, (start, end) in enumerate(zip(path, path[1:], strict=False)):
        candidate, _ = _nearest_on_segment(pivot, start, end)
        distance = _norm(_sub(candidate, pivot))
        if distance < closest_distance:
            closest_point = candidate
            closest_segment = index
            closest_distance = distance

    if tail_index == -1:
        points = (closest_point, *path[closest_segment + 1 :])
    else:
        stop = closest_segment + 1
        points = (closest_point, *reversed(path[:stop]))
    cleaned = tuple(
        point for index, point in enumerate(points) if index == 0 or point != points[index - 1]
    )
    if len(cleaned) < 2:
        raise ValueError("path has no branch extending away from pivot")
    return cleaned


def _point_at_radius(path: Polyline, pivot: Point, radius: float) -> Point:
    for start, end in zip(path, path[1:], strict=False):
        start_radius = _norm(_sub(start, pivot))
        end_radius = _norm(_sub(end, pivot))
        if min(start_radius, end_radius) <= radius <= max(start_radius, end_radius):
            share = (
                0.0
                if end_radius == start_radius
                else (radius - start_radius) / (end_radius - start_radius)
            )
            return _add(start, _scale(_sub(end, start), share))
    return min(path, key=lambda point: abs(_norm(_sub(point, pivot)) - radius))


def _point_segment_distance(point: Point, segment: Segment) -> float:
    nearest, _ = _nearest_on_segment(point, *segment)
    return _norm(_sub(point, nearest))


def _segment_distance(first: Segment, second: Segment) -> float:
    if segments_intersect(*first, *second):
        return 0.0
    return min(
        _point_segment_distance(first[0], second),
        _point_segment_distance(first[1], second),
        _point_segment_distance(second[0], first),
        _point_segment_distance(second[1], first),
    )


def _segments(path: Polyline) -> tuple[Segment, ...]:
    return tuple(zip(path, path[1:], strict=False))


def _clear_of_path(first: Polyline, second: Polyline, clearance: float) -> bool:
    for first_segment in _segments(first):
        for second_segment in _segments(second):
            distance = _segment_distance(first_segment, second_segment)
            if distance < clearance or (clearance == 0 and distance == 0):
                return False
    return True


def _clear_of_obstacles(path: Polyline, obstacles: Obstacles, clearance: float) -> bool:
    candidate_segments = _segments(path)
    if any(
        _segment_distance(candidate, obstacle) < clearance
        or (clearance == 0 and segments_intersect(*candidate, *obstacle))
        for candidate in candidate_segments
        for obstacle in obstacles.segments
    ):
        return False
    if any(
        rect_hits_segment(rect.inflate(clearance), *segment)
        for rect in obstacles.rects
        for segment in candidate_segments
    ):
        return False
    for polygon in obstacles.polygons:
        if any(point_in_polygon(point, polygon) for point in path):
            return False
        if any(
            _segment_distance(candidate, edge) < clearance
            or (clearance == 0 and segments_intersect(*candidate, *edge))
            for candidate in candidate_segments
            for edge in polygon_edges(polygon)
        ):
            return False
    return True


def place_rotation_marker(
    old_path: Sequence[Point],
    new_path: Sequence[Point],
    pivot: Point,
    bounds: Rect,
    connector: Connector,
    *,
    obstacles: Obstacles = _NO_OBSTACLES,
    accepted: Sequence[Sequence[Point]] = (),
    clearance: float = 0.0,
    search_step: float = 1.0,
    minimum_span: float = 0.0,
) -> RotationPlacement | None:
    """Find the outermost collision-free rotation connector.

    ``old_path`` and ``new_path`` are polylines in display coordinates. Their
    branches on the same side of ``pivot`` are selected automatically. Search
    starts at the shorter usable tail and moves inward by ``search_step``. The
    caller supplies ``connector`` so layout stays independent of any curve
    package; it receives ``(start, end, pivot)`` and returns sampled points.

    Source paths should not also be listed as obstacles: touching them at the
    connector endpoints is intentional. ``None`` means no candidate satisfies
    the bounds, span, and obstacle constraints.
    """
    old = tuple(old_path)
    new = tuple(new_path)
    if len(old) < 2 or len(new) < 2:
        raise ValueError("rotation placement requires two paths with at least two points")
    if clearance < 0 or minimum_span < 0:
        raise ValueError("clearance and minimum_span must be non-negative")
    if not math.isfinite(search_step) or search_step <= 0:
        raise ValueError("search_step must be finite and positive")

    old_branch = _branch(old, pivot)
    old_direction = _unit(_sub(old_branch[-1], pivot))
    new_branch = _branch(new, pivot, old_direction)
    available = min(
        _norm(_sub(old_branch[-1], pivot)),
        _norm(_sub(new_branch[-1], pivot)),
    )
    accepted_paths = tuple(tuple(path) for path in accepted)
    inner_bounds = bounds.inflate(-clearance)
    radius = available
    while radius > 0:
        start = _point_at_radius(old_branch, pivot, radius)
        end = _point_at_radius(new_branch, pivot, radius)
        if _norm(_sub(end, start)) >= minimum_span:
            path = tuple(connector(start, end, pivot))
            if len(path) < 2:
                raise ValueError("connector must return at least two points")
            if (
                all(inner_bounds.contains(point) for point in path)
                and _clear_of_obstacles(path, obstacles, clearance)
                and all(_clear_of_path(path, other, clearance) for other in accepted_paths)
            ):
                return RotationPlacement(path, start, end, radius, radius / available)
        radius -= search_step
    return None


def extend_polyline_tail(path: Sequence[Point], distance: float) -> Polyline:
    """Append a point ``distance`` display units beyond a polyline's tail tangent."""
    points = tuple(path)
    if len(points) < 2:
        raise ValueError("tail extension requires at least two points")
    if not math.isfinite(distance) or distance < 0:
        raise ValueError("distance must be finite and non-negative")
    if distance == 0:
        return points
    tangent = _unit(_sub(points[-1], points[-2]))
    return (*points, _add(points[-1], _scale(tangent, distance)))


def tail_label_position(
    path: Sequence[Point],
    size: tuple[float, float],
    gap: float = 0.0,
) -> Point:
    """Place a label's bottom-center anchor on the continuation of a path tail.

    The returned display point is the label's bottom-center anchor. It is moved
    just far enough along the tail tangent that the label rectangle, inflated by
    ``gap``, no longer contains the curve endpoint.
    """
    points = tuple(path)
    if len(points) < 2:
        raise ValueError("tail label placement requires at least two points")
    width, height = size
    invalid_number = not all(math.isfinite(value) for value in (*size, gap))
    if width < 0 or height < 0 or gap < 0 or invalid_number:
        raise ValueError("label size and gap must be finite and non-negative")
    tangent = _unit(_sub(points[-1], points[-2]))
    tx, ty = tangent
    exits = []
    if tx > 0:
        exits.append((width / 2 + gap) / tx)
    elif tx < 0:
        exits.append((width / 2 + gap) / -tx)
    if ty > 0:
        exits.append(gap / ty)
    elif ty < 0:
        exits.append((height + gap) / -ty)
    distance = math.nextafter(min(exits), math.inf)
    position = _add(points[-1], _scale(tangent, distance))
    return (
        math.nextafter(position[0], math.inf if tx > 0 else -math.inf if tx < 0 else position[0]),
        math.nextafter(position[1], math.inf if ty > 0 else -math.inf if ty < 0 else position[1]),
    )
