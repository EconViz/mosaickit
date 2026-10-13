from __future__ import annotations

import re
import warnings
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mosaickit.canvas.canvas import Canvas
from mosaickit.errors import ConfigurationError, RenderError
from mosaickit.parameter import Parameter, ParameterValues
from mosaickit.rendering import RenderCache, Renderer
from mosaickit.scene import Scene

_DEPRECATION_MESSAGE = (
    "MosaicKit Animation and Animation.sweep() are deprecated; use KineticKit for animation. "
    "These compatibility APIs may be removed in the next release."
)


@dataclass(frozen=True, slots=True)
class Animation:
    template: Canvas
    parameter: Parameter
    values: tuple[Any, ...]
    fps: int = 30

    def __post_init__(self) -> None:
        if isinstance(self.fps, bool) or not isinstance(self.fps, int) or self.fps < 1:
            raise ConfigurationError("Animation.fps must be a positive integer")
        values = ParameterValues(self.parameter, self.values).values
        if not values:
            raise ConfigurationError("Animation requires at least one value")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "template", self.template.copy())
        warnings.warn(
            _DEPRECATION_MESSAGE,
            DeprecationWarning,
            stacklevel=3,  # Skip __post_init__ and the generated dataclass __init__.
        )

    @staticmethod
    def sweep(canvas: Canvas, values: ParameterValues, *, fps: int = 30) -> Animation:
        # Only suppress this constructor's warning, then attribute it to the sweep caller.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=f"^{re.escape(_DEPRECATION_MESSAGE)}$",
                category=DeprecationWarning,
            )
            animation = Animation(canvas, values.parameter, values.values, fps)
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
        return animation

    def frames(self) -> Iterator[Scene]:
        for value in self.values:
            yield self.template.bind(self.parameter, value).snapshot()

    def save(
        self,
        path: str | Path,
        *,
        renderer: Renderer | str | None = None,
        cache: RenderCache | None = None,
    ) -> list[Path]:
        selected = self.template._renderer(renderer)
        if not hasattr(selected, "save_animation"):
            raise RenderError(f"Renderer {selected.name!r} does not support animation output")
        return selected.save_animation(
            self, Path(path), cache if cache is not None else RenderCache()
        )
