from mosaickit.palette import DEFAULT_PALETTE as P
from mosaickit.styles import DashStyle, Fill, LegendStyle, Marker, Stroke, TextStyle
from mosaickit.themes.theme import StyleBundle, Theme

PRIMITIVE_DEFAULT = StyleBundle(
    stroke=Stroke(color=P["grey-800"], width=1.5, dash=DashStyle.SOLID, opacity=1),
    fill=Fill(color=P["grey-200"], opacity=0.3, hatch=""),
    marker=Marker(
        color=P["grey-800"],
        size=36,
        shape="o",
        opacity=1,
        edge_color=P["grey-800"],
        edge_width=0,
    ),
    text=TextStyle(
        color=P["grey-900"], size=12, family="DejaVu Sans", weight="normal", opacity=1, rotation=0
    ),
    legend=LegendStyle(visible=True, location="best", frame=False, size=10),
)

default = Theme(
    "default",
    {
        "primary": StyleBundle(stroke=Stroke(color=P["blue"])),
        "secondary": StyleBundle(stroke=Stroke(color=P["red"])),
        "accent": StyleBundle(stroke=Stroke(color=P["teal"])),
        "guide": StyleBundle(stroke=Stroke(color=P["grey-400"], dash=DashStyle.DASHED)),
        "axes": StyleBundle(stroke=Stroke(color=P["grey-800"], width=1)),
        "canvas": StyleBundle(fill=Fill(color=P["white"], opacity=1)),
    },
)
