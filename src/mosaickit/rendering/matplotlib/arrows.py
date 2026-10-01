"""Figure-local arrowheads aligned with path endpoint tangents."""

from matplotlib.patches import FancyArrowPatch

from mosaickit.styles import ArrowPlacement, ArrowStyle


def _arrow_style(style, placement):
    if style == ArrowStyle.OPEN:
        return {ArrowPlacement.START: "<-", ArrowPlacement.END: "->", ArrowPlacement.BOTH: "<->"}[
            placement
        ]
    if style == ArrowStyle.TRIANGLE or placement == ArrowPlacement.BOTH:
        return {
            ArrowPlacement.START: "<|-",
            ArrowPlacement.END: "-|>",
            ArrowPlacement.BOTH: "<|-|>",
        }[placement]
    return "fancy" if style == ArrowStyle.FANCY else "wedge"


def add_arrow(ax, start, end, stroke, placement, zorder=0):
    style = stroke.arrow or ArrowStyle.OPEN
    if placement == ArrowPlacement.START and style in (ArrowStyle.FANCY, ArrowStyle.WEDGE):
        start, end = end, start
    color = stroke.color
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle=_arrow_style(style, placement),
        mutation_scale=12,
        linewidth=stroke.width,
        color=(color.red, color.green, color.blue, color.alpha * stroke.opacity),
        shrinkA=0,
        shrinkB=0,
        zorder=zorder,
    )
    ax.add_patch(arrow)
    return arrow


def add_path_arrows(ax, path, stroke, placement, zorder):
    vertices = path.vertices
    if placement in (ArrowPlacement.START, ArrowPlacement.BOTH):
        for point in vertices[1:]:
            if tuple(point) != tuple(vertices[0]):
                near = vertices[0] + (point - vertices[0]) * 0.15
                add_arrow(ax, near, vertices[0], stroke, ArrowPlacement.END, zorder)
                break
    if placement in (ArrowPlacement.END, ArrowPlacement.BOTH):
        for point in reversed(vertices[:-1]):
            if tuple(point) != tuple(vertices[-1]):
                near = vertices[-1] + (point - vertices[-1]) * 0.15
                add_arrow(ax, near, vertices[-1], stroke, ArrowPlacement.END, zorder)
                break
