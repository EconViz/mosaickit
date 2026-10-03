"""Measure gutter text in display pixels before anything is placed."""

from typing import Any

from mosaickit.rendering.matplotlib.fonts import font_properties


def as_drawn(text: str, math: bool) -> str:
    return f"${text}$" if math and not (text.startswith("$") and text.endswith("$")) else text


def measure(ax: Any, text: str, style: Any, renderer: Any) -> tuple[float, float]:
    probe = ax.text(0, 0, text, fontproperties=font_properties(style), multialignment="center")
    box = probe.get_window_extent(renderer)
    probe.remove()
    return box.width, box.height
