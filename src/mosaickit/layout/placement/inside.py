"""Can the label sit inside its own region?"""

from mosaickit.layout.geometry import Polygon, Rect, polylabel, rect_inside_polygon
from mosaickit.layout.placement.obstacles import Obstacles, count_violations


def fits_inside(
    polygon: Polygon, size: tuple[float, float], obstacles: Obstacles, bounds: Rect
) -> Rect | None:
    """The rect centred on the region's pole, if it fits and touches nothing else."""
    own = tuple(polygon)
    rect = Rect.centered(polylabel(own), *size)
    if not rect_inside_polygon(rect, own):
        return None
    others = tuple(p for p in obstacles.polygons if p != own)
    return rect if count_violations(rect, obstacles, bounds, others) == 0 else None
