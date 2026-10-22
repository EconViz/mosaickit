from typing import Any

from matplotlib.font_manager import FontProperties

from mosaickit.rendering.matplotlib.text_layout import configured_file
from mosaickit.rendering.matplotlib.typesetting import typeset


def font_properties(style) -> FontProperties:
    """Matplotlib's font for ``style``: your file for its generic font when you gave one."""
    path = configured_file(style.font or "sans")
    if path is not None:
        return FontProperties(fname=path, size=style.size, weight=style.weight)
    return FontProperties(size=style.size, weight=style.weight)


def measure_text(ax: Any, text: str, style: Any, renderer: Any) -> tuple[float, float]:
    """Width and height in display pixels of ``text`` drawn in ``style``."""
    layout = typeset(text, style)
    if layout is not None:
        return layout.measure(ax.figure.dpi / 72, style.rotation)
    probe = ax.text(
        0,
        0,
        text,
        fontproperties=font_properties(style),
        rotation=style.rotation,
        ha="center",
        va="center",
    )
    box = probe.get_window_extent(renderer)
    probe.remove()
    return box.width, box.height
