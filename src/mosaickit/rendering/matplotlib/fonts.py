from matplotlib.font_manager import FontProperties


def font_properties(style) -> FontProperties:
    return FontProperties(family=style.family, size=style.size, weight=style.weight)
