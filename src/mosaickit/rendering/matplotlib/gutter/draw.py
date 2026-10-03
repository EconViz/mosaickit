"""Draw gutter texts; braces and inside brace labels come from the shared brace code."""

from typing import Any

from mosaickit.rendering.matplotlib.gutter.frame import AxisFrame
from mosaickit.rendering.matplotlib.gutter.place import GutterText
from mosaickit.rendering.matplotlib.labels import draw_label


def draw_text(ax: Any, frame: AxisFrame, item: GutterText) -> Any:
    """A mark, note, or outside brace label, aligned to face the plot."""
    return draw_label(
        ax,
        item.resolved.style.text,
        item.text,
        item.anchor,
        gid=item.gid,
        z_index=item.resolved.layer.z_index,
        align=frame.facing,
    )
