from mosaickit.rendering.tikz.options import fill_options, stroke_options, text_options
from mosaickit.styles import Fill, Stroke, TextStyle

TRANSLATORS = {
    Stroke: stroke_options.translate,
    Fill: fill_options.translate,
    TextStyle: text_options.translate,
}
