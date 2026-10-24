"""Draw gutter texts; braces and inside brace labels come from the shared brace code."""

from typing import Any

from mosaickit.layout import Rect
from mosaickit.rendering.matplotlib.gutter.frame import AxisFrame
from mosaickit.rendering.matplotlib.gutter.place import GutterText
from mosaickit.rendering.matplotlib.labels import draw_label, nudged


def draw_text(ax: Any, frame: AxisFrame, item: GutterText) -> Any:
    """A mark, note, or outside brace label, aligned to face the plot.

    An outside brace label honours its layer's ``nudge``; the brace outline stays put. Marks
    and notes have no nudge: they are spread along the axis so they never overlap.
    """
    x, y = item.anchor
    moved, _ = nudged(ax, getattr(item.resolved.layer, "nudge", None), Rect(x, y, x, y))
    return draw_label(
        ax,
        item.resolved.style.text,
        item.text,
        moved.center,
        gid=item.gid,
        z_index=item.resolved.layer.z_index,
        align=frame.facing,
    )
