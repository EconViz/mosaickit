"""Register how MosaicKit's own layer types are drawn. The only module that pairs
scene layer types with Matplotlib drawing code."""

from mosaickit.rendering.matplotlib.artists import (
    arrow_artist,
    fill_artist,
    marker_artist,
    path_artist,
    text_artist,
)
from mosaickit.rendering.matplotlib.gutter import gutter_pass
from mosaickit.rendering.matplotlib.legend import legend_pass
from mosaickit.rendering.matplotlib.point_labels import point_label_pass
from mosaickit.rendering.matplotlib.region_labels import region_label_pass
from mosaickit.rendering.matplotlib.registry import register_builder, register_pass
from mosaickit.rendering.matplotlib.span_braces import span_brace_pass
from mosaickit.scene import (
    ArrowLayer,
    AxisLayer,
    FillLayer,
    LegendLayer,
    MarkerLayer,
    PathLayer,
    PointLabelLayer,
    RegionLabelLayer,
    SpanBraceLayer,
    TextLayer,
)

register_builder(PathLayer, path_artist.build)
register_builder(FillLayer, fill_artist.build)
register_builder(MarkerLayer, marker_artist.build)
register_builder(TextLayer, text_artist.build)
register_builder(ArrowLayer, arrow_artist.build)

# Order matters: each pass avoids everything drawn before it.
# - Axis marks, notes, and braces sit at fixed places along the axes, so they go first.
# - Braces between two points sit at fixed places too; their labels avoid the above.
# - Point labels must sit right beside their point and have few positions to choose from.
# - Region callouts can move much further out (with a leader) to avoid both.
# - Legends come last: Matplotlib positions them, not MosaicKit's layout.
register_pass(AxisLayer, gutter_pass)
register_pass(SpanBraceLayer, span_brace_pass)
register_pass(PointLabelLayer, point_label_pass)
register_pass(RegionLabelLayer, region_label_pass)
register_pass(LegendLayer, legend_pass)
