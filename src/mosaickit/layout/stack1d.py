"""One-dimensional layout: de-overlap items on a line, and pack intervals into lanes."""

from __future__ import annotations

from collections.abc import Sequence


def spread(centers: Sequence[float], sizes: Sequence[float], gap: float = 0.0) -> tuple[float, ...]:
    """Move items apart so none overlap, keeping their order.

    Each item ``i`` occupies ``centers[i] ± sizes[i] / 2`` and neighbours keep at
    least ``gap`` between them. Overlapping runs merge into clusters that are
    packed tightly and centred on their members' mean target, which minimises
    the total squared displacement. Equal centres keep their input order.
    """
    if len(centers) != len(sizes):
        raise ValueError("centers and sizes must have the same length")
    if any(size < 0 for size in sizes):
        raise ValueError("sizes must be non-negative")
    order = sorted(range(len(centers)), key=lambda i: centers[i])
    clusters: list[tuple[list[int], float]] = []  # (members, start of the packed block)

    def length(members: list[int]) -> float:
        return sum(sizes[j] for j in members) + gap * (len(members) - 1)

    for i in order:
        clusters.append(([i], centers[i] - sizes[i] / 2))
        while len(clusters) > 1:
            (first, first_start), (second, second_start) = clusters[-2], clusters[-1]
            if first_start + length(first) + gap <= second_start:
                break
            members = first + second
            offsets, along = [], 0.0
            for j in members:
                offsets.append(along + sizes[j] / 2)
                along += sizes[j] + gap
            start = sum(centers[j] - o for j, o in zip(members, offsets, strict=True))
            clusters[-2:] = [(members, start / len(members))]
    placed = [0.0] * len(centers)
    for members, start in clusters:
        along = start
        for j in members:
            placed[j] = along + sizes[j] / 2
            along += sizes[j] + gap
    return tuple(placed)


def assign_lanes(intervals: Sequence[tuple[float, float]], gap: float = 0.0) -> tuple[int, ...]:
    """Give each interval the first lane where it keeps ``gap`` from the lane's others.

    Intervals are taken in input order, so earlier ones stay closest to lane 0.
    """
    lanes: list[list[tuple[float, float]]] = []
    result = []
    for a, b in intervals:
        lo, hi = min(a, b), max(a, b)
        for index, lane in enumerate(lanes):
            if all(hi + gap <= other_lo or other_hi + gap <= lo for other_lo, other_hi in lane):
                lane.append((lo, hi))
                result.append(index)
                break
        else:
            lanes.append([(lo, hi)])
            result.append(len(lanes) - 1)
    return tuple(result)
