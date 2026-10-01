from dataclasses import dataclass

from mosaickit.canvas.canvas import Canvas
from mosaickit.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class Span:
    canvas: Canvas
    rows: int = 1
    cols: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.canvas, Canvas):
            raise ConfigurationError("Span.canvas must be a Canvas")
        for name in ("rows", "cols"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ConfigurationError(f"Span.{name} must be a positive integer")
