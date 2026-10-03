"""Segment intersection tests."""

from mosaickit.layout.geometry.rect import Point, Rect


def _orient(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: Point, b: Point, p: Point) -> bool:
    return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])


def segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    """Whether segment ``ab`` touches segment ``cd``, including endpoints and overlaps."""
    d1, d2 = _orient(c, d, a), _orient(c, d, b)
    d3, d4 = _orient(a, b, c), _orient(a, b, d)
    if d1 * d2 < 0 and d3 * d4 < 0:
        return True
    return (
        (d1 == 0 and _on_segment(c, d, a))
        or (d2 == 0 and _on_segment(c, d, b))
        or (d3 == 0 and _on_segment(a, b, c))
        or (d4 == 0 and _on_segment(a, b, d))
    )


def rect_hits_segment(rect: Rect, a: Point, b: Point) -> bool:
    if rect.contains(a) or rect.contains(b):
        return True
    return any(segments_intersect(a, b, p, q) for p, q in rect.edges())
