from mosaickit.rendering.matplotlib.artists import (
    fill_artist,
    marker_artist,
    path_artist,
    text_artist,
)
from mosaickit.scene import FillLayer, MarkerLayer, PathLayer, TextLayer

BUILDERS = {
    PathLayer: path_artist.build,
    FillLayer: fill_artist.build,
    MarkerLayer: marker_artist.build,
    TextLayer: text_artist.build,
}
