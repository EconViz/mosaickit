from mosaickit.rendering.tikz.options.stroke_options import color_option


def translate(style) -> str:
    weight = r"\bfseries" if style.weight in ("bold", "heavy") else r"\mdseries"
    family = (
        r"\ttfamily"
        if style.family == "monospace"
        else (r"\rmfamily" if style.family == "serif" else r"\sffamily")
    )
    font = f"\\fontsize{{{style.size:g}}}{{{style.size * 1.2:g}}}\\selectfont{family}{weight}"
    return (
        f"text={color_option(style.color)},text opacity={style.opacity * style.color.alpha:g},"
        f"font={{{font}}},rotate={style.rotation:g}"
    )
