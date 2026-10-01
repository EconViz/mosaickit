from mosaickit.styles import DashStyle, Fill, LegendStyle, Marker, Stroke, TextStyle
from mosaickit.themes.theme import StyleBundle, Theme

PRIMITIVE_DEFAULT = StyleBundle(
    stroke=Stroke(color="#333333", width=1.5, dash=DashStyle.SOLID, opacity=1),
    fill=Fill(color="#CCCCCC", opacity=0.3, hatch=""),
    marker=Marker(
        color="#333333", size=36, shape="o", opacity=1, edge_color="#333333", edge_width=0
    ),
    text=TextStyle(
        color="#222222", size=12, family="DejaVu Sans", weight="normal", opacity=1, rotation=0
    ),
    legend=LegendStyle(visible=True, location="best", frame=False, size=10),
)

default = Theme(
    "default",
    {
        "primary": StyleBundle(stroke=Stroke(color="#377EB8")),
        "secondary": StyleBundle(stroke=Stroke(color="#E41A1C")),
        "accent": StyleBundle(stroke=Stroke(color="#984EA3")),
        "guide": StyleBundle(stroke=Stroke(color="#999999", dash=DashStyle.DASHED)),
        "axes": StyleBundle(stroke=Stroke(color="#333333", width=1)),
        "canvas": StyleBundle(fill=Fill(color="#FFFFFF", opacity=1)),
    },
)
