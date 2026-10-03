from dataclasses import dataclass, field
from typing import Any, ClassVar

from mosaickit.errors import ConfigurationError
from mosaickit.scene.layer import Layer, _geometry
from mosaickit.styles import Stroke, TextStyle

REGION_LABEL_PLACEMENTS = ("auto", "inside", "callout")


@dataclass(frozen=True, slots=True)
class RegionLabelLayer(Layer):
    """Name a filled region: inside it when the text fits, otherwise as a callout.

    ``region`` is a ``FillLayer`` id or a polygon. ``stroke`` styles the callout leader.
    """

    role: str = field(default="text", kw_only=True)
    region: Any
    text: str
    short_text: str | None = None
    placement: str = "auto"
    style: TextStyle | None = None
    stroke: Stroke | None = Stroke(width=0.8)
    fallback_category: ClassVar[str] = "text"

    def __post_init__(self) -> None:
        Layer.__post_init__(self)
        if isinstance(self.region, str):
            if not self.region:
                raise ConfigurationError("RegionLabelLayer.region must be a layer id or polygon")
        else:
            object.__setattr__(self, "region", _geometry(self.region, minimum=3))
        if not isinstance(self.text, str) or not self.text:
            raise ConfigurationError("RegionLabelLayer.text must be a non-empty string")
        if self.short_text is not None and (
            not isinstance(self.short_text, str) or not self.short_text
        ):
            raise ConfigurationError("RegionLabelLayer.short_text must be a non-empty string")
        if self.placement not in REGION_LABEL_PLACEMENTS:
            raise ConfigurationError(f"Unsupported region label placement: {self.placement}")
