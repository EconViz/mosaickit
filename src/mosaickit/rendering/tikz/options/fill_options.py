from mosaickit.errors import RenderError
from mosaickit.rendering.tikz.options.stroke_options import color_option


def translate(style) -> str:
    result = f"fill={color_option(style.color)},fill opacity={style.opacity * style.color.alpha:g}"
    if style.hatch:
        patterns = {
            "/": "north east lines",
            "\\": "north west lines",
            "|": "vertical lines",
            "-": "horizontal lines",
            "+": "grid",
            "x": "crosshatch",
            ".": "dots",
        }
        if style.hatch not in patterns:
            raise RenderError(f"Unsupported TikZ hatch: {style.hatch!r}")
        result += f",pattern={patterns[style.hatch]},pattern color={color_option(style.color)}"
    return result
