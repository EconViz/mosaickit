"""True text extents with the configured fonts, for label placement."""

from __future__ import annotations

from collections.abc import Callable

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from mosaickit.math_font import MathFont
from mosaickit.rendering.matplotlib.fonts import measure_text
from mosaickit.rendering.matplotlib.typesetting import typesetting
from mosaickit.styles import TextStyle
from mosaickit.text_fonts import TextFonts

POINTS_DPI = 72.0
"""At this dpi one display pixel is one point, so measured extents come out in points."""


def text_measurer(
    size: float,
    *,
    weight: str | int | None = None,
    font: str | None = None,
    math_font: MathFont | None = None,
    text_fonts: TextFonts | None = None,
) -> Callable[[str], tuple[float, float]]:
    """A function giving the real ``(width, height)`` in points of a text at ``size`` points.

    It sets the text with the same GlyphKit (or Matplotlib) layout the renderer draws with, in
    the fonts you pass, so the box is the one drawn, not an estimate. Pass it to
    :func:`mosaickit.labels.place_scene_labels`. The size is never altered.
    """
    style = TextStyle(size=size, weight=weight, font=font, rotation=0.0)
    figure = Figure(dpi=POINTS_DPI)
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_subplot()
    renderer = canvas.get_renderer()
    cache: dict[str, tuple[float, float]] = {}

    def measure(text: str) -> tuple[float, float]:
        if text not in cache:
            with typesetting(math_font, text_fonts):
                width, height = measure_text(axes, text, style, renderer)
                cache[text] = (float(width), float(height))
        return cache[text]

    return measure
