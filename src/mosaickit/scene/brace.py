from dataclasses import dataclass, field
from typing import Any

from mosaickit.errors import ConfigurationError
from mosaickit.scene.axis_layer import AxisLayer, _axis_value
from mosaickit.scene.brace_parts import BraceParts

BRACE_SIDES = ("inside", "outside")


@dataclass(frozen=True, slots=True)
class BraceLayer(BraceParts, AxisLayer):
    """A curly brace over ``start``..``end`` on an axis, with an optional label.

    ``side="inside"`` draws it just inside the plot, its label placed so it covers
    nothing; ``"outside"`` draws it in the gutter, past the axis marks.
    """

    role: str = field(default="axes", kw_only=True)
    start: Any
    end: Any
    label: str | None = None
    side: str = "inside"

    def __post_init__(self) -> None:
        AxisLayer.__post_init__(self)
        for name in ("start", "end"):
            value = _axis_value(f"BraceLayer.{name}", getattr(self, name))
            object.__setattr__(self, name, value)
        if self.start == self.end:
            raise ConfigurationError("BraceLayer needs start != end")
        self._check_label("BraceLayer")
        if self.side not in BRACE_SIDES:
            raise ConfigurationError(f"Unsupported brace side: {self.side!r}")
