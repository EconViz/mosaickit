"""Register how MosaicKit's own layer types are drawn. The only module that pairs
scene layer types with Matplotlib drawing code."""

from mosaickit.rendering.matplotlib.artists import (
    arrow_artist,
    fill_artist,
    marker_artist,
    path_artist,
    text_artist,
)
from mosaickit.rendering.matplotlib.legend import legend_pass
from mosaickit.rendering.matplotlib.region_labels import region_label_pass
from mosaickit.rendering.matplotlib.registry import register_builder, register_pass
from mosaickit.scene import (
    ArrowLayer,
    FillLayer,
    LegendLayer,
    MarkerLayer,
    PathLayer,
    RegionLabelLayer,
    TextLayer,
)

register_builder(PathLayer, path_artist.build)
register_builder(FillLayer, fill_artist.build)
register_builder(MarkerLayer, marker_artist.build)
register_builder(TextLayer, text_artist.build)
register_builder(ArrowLayer, arrow_artist.build)

# Order matters: labels avoid everything drawn so far; legends come last.
register_pass(RegionLabelLayer, region_label_pass)
register_pass(LegendLayer, legend_pass)
