"""Place a label beside an anchor (such as a brace tip) without covering anything.

Candidates sit past the anchor across the axis, nearest first; at each distance
the label may slide along the axis by up to ``reach`` from the anchor, smallest
shift first. The first candidate that covers nothing wins.
"""

from mosaickit.layout.geometry import Point, Rect
from mosaickit.layout.placement.obstacles import Obstacles, count_violations

GAPS = (3.0, 8.0, 14.0, 22.0, 32.0, 45.0)  # pt past the anchor
STEP = 3.0  # pt between sliding positions


def _shifts(reach: float, step: float) -> list[float]:
    shifts = [0.0]
    k = 1
    while k * step <= reach:
        shifts += [k * step, -k * step]
        k += 1
    return shifts


def place_beside(
    anchor: Point,
    size: tuple[float, float],
    *,
    axis: str,
    direction: int,
    reach: float,
    obstacles: Obstacles,
    bounds: Rect,
    scale: float = 1.0,
) -> tuple[Rect, int]:
    """The label rect and how many obstacles it covers (0 when a free spot exists).

    ``axis`` is the axis the anchor's span runs along: on ``"y"`` the label goes
    left or right of the anchor, on ``"x"`` above or below it.
    """
    width, height = size
    ax_, ay = anchor
    best: tuple[int, Rect] | None = None
    for gap in GAPS:
        for shift in _shifts(reach, STEP * scale):
            if axis == "y":
                x0 = ax_ + gap * scale if direction > 0 else ax_ - gap * scale - width
                rect = Rect(x0, ay + shift - height / 2, x0 + width, ay + shift + height / 2)
            else:
                y0 = ay + gap * scale if direction > 0 else ay - gap * scale - height
                rect = Rect(ax_ + shift - width / 2, y0, ax_ + shift + width / 2, y0 + height)
            violations = count_violations(rect, obstacles, bounds, obstacles.polygons)
            if violations == 0:
                return rect, 0
            if best is None or violations < best[0]:
                best = (violations, rect)
    assert best is not None
    return best[1], best[0]
