from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

from mosaickit.scene.axis_layer import AxisLayer, _axis_value, _text
from mosaickit.styles import TextStyle


@dataclass(frozen=True, slots=True)
class AxisMarkLayer(AxisLayer):
    """A short symbol next to the axis at ``value``, outside the plot."""

    role: str = field(default="axes", kw_only=True)
    value: Any
    label: str
    math: bool = False
    style: TextStyle | None = None
    fallback_category: ClassVar[str] = "text"
    style_slots: ClassVar[Mapping[str, str]] = {"text": "style"}

    def __post_init__(self) -> None:
        AxisLayer.__post_init__(self)
        object.__setattr__(self, "value", _axis_value("AxisMarkLayer.value", self.value))
        _text("AxisMarkLayer.label", self.label)
