from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

from mosaickit.errors import ConfigurationError
from mosaickit.scene.axis_layer import _text
from mosaickit.scene.layer import Layer, _point
from mosaickit.styles import Stroke, TextStyle

HORIZONTAL_SIDES = ("above", "below")
VERTICAL_SIDES = ("left", "right")


@dataclass(frozen=True, slots=True)
class SpanBraceLayer(Layer):
    """A curly brace between two points inside the plot, with an optional label.

    The span is horizontal (``side`` ``"above"`` or ``"below"``) or vertical
    (``"left"`` or ``"right"``). The brace bulges to ``side`` and its label sits
    past the tip, placed so it covers nothing.
    """

    role: str = field(default="axes", kw_only=True)
    start: Any
    end: Any
    label: str | None = None
    side: str = "below"
    math: bool = False
    style: TextStyle | None = None
    stroke: Stroke | None = None
    fallback_category: ClassVar[str] = "text"
    style_slots: ClassVar[Mapping[str, str]] = {"stroke": "stroke", "text": "style"}

    def __post_init__(self) -> None:
        Layer.__post_init__(self)
        start, end = _point(self.start), _point(self.end)
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)
        if start == end:
            raise ConfigurationError("SpanBraceLayer needs start != end")
        if self.label is not None:
            _text("SpanBraceLayer.label", self.label)
        if start[1] == end[1]:
            allowed = HORIZONTAL_SIDES
        elif start[0] == end[0]:
            allowed = VERTICAL_SIDES
        else:
            raise ConfigurationError("SpanBraceLayer spans must be horizontal or vertical")
        if self.side not in allowed:
            raise ConfigurationError(
                f"SpanBraceLayer side {self.side!r} must be one of {allowed} for this span"
            )
