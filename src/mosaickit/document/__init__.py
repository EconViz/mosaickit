"""The scene document: a versioned, JSON-compatible form of a ``Scene``.

Data only. How a document travels, and anything that updates one in place, is not this
package's business.
"""

from mosaickit.document.codec import (
    FORMAT,
    MAX_DEPTH,
    MAX_NODES,
    MAX_STRING,
    VERSION,
    scene_from_dict,
    scene_from_json,
    scene_to_dict,
    scene_to_json,
)

__all__ = [
    "FORMAT",
    "MAX_DEPTH",
    "MAX_NODES",
    "MAX_STRING",
    "VERSION",
    "scene_from_dict",
    "scene_from_json",
    "scene_to_dict",
    "scene_to_json",
]
