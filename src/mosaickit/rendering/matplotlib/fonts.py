from typing import Any

from matplotlib.font_manager import FontProperties


def font_properties(style) -> FontProperties:
    return FontProperties(family=style.family, size=style.size, weight=style.weight)


def measure_text(ax: Any, text: str, style: Any, renderer: Any) -> tuple[float, float]:
    """Width and height in display pixels of ``text`` drawn in ``style``."""
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
