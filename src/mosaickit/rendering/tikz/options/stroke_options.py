from mosaickit.colors import Color
from mosaickit.styles import ArrowPlacement, ArrowStyle, DashStyle


def color_option(color: Color) -> str:
    return f"{{rgb,1:red,{color.red:g};green,{color.green:g};blue,{color.blue:g}}}"


def translate(style, placement=ArrowPlacement.END) -> str:
    parts = [
        f"draw={color_option(style.color)}",
        f"line width={style.width:g}pt",
        f"draw opacity={style.opacity * style.color.alpha:g}",
        {
            DashStyle.SOLID: "solid",
            DashStyle.DASHED: "dashed",
            DashStyle.DOTTED: "dotted",
            DashStyle.DASHDOT: "dash dot",
        }[style.dash],
    ]
    if style.arrow:
        tip = {
            ArrowStyle.OPEN: "Latex[open]",
            ArrowStyle.TRIANGLE: "Latex",
            ArrowStyle.FANCY: "Stealth",
            ArrowStyle.WEDGE: "Triangle",
        }[style.arrow]
        start = tip if placement in (ArrowPlacement.START, ArrowPlacement.BOTH) else ""
        end = tip if placement in (ArrowPlacement.END, ArrowPlacement.BOTH) else ""
        parts.append(f"{{{start}}}-{{{end}}}")
    return ",".join(parts)
