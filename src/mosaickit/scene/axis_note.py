from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

from mosaickit.scene.axis_layer import AxisLayer, _axis_value
from mosaickit.scene.layer import _text
from mosaickit.styles import TextStyle


@dataclass(frozen=True, slots=True)
class AxisNoteLayer(AxisLayer):
    """An explanation for ``value``, in the outermost gutter column. May span lines."""

    role: str = field(default="axes.note", kw_only=True)
    value: Any
    text: str
    style: TextStyle | None = None
    fallback_category: ClassVar[str] = "text"
    style_slots: ClassVar[Mapping[str, str]] = {"text": "style"}

    def __post_init__(self) -> None:
        AxisLayer.__post_init__(self)
        object.__setattr__(self, "value", _axis_value("AxisNoteLayer.value", self.value))
        _text("AxisNoteLayer.text", self.text)
