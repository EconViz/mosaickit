"""Axis presets assembled exclusively from ordinary scene primitives."""

from dataclasses import dataclass

from mosaickit.errors import ConfigurationError
from mosaickit.interval import Interval
from mosaickit.scene.layer import Layer
from mosaickit.scene.path import PathLayer
from mosaickit.scene.text import TextLayer
from mosaickit.styles import ArrowPlacement, ArrowStyle, Stroke

TITLE_GAP = 6.0  # pt between an axis end (or arrow tip) and its title


@dataclass(frozen=True, slots=True)
class AxisSpec:
    extent: tuple[float, float]
    arrow: ArrowPlacement | None = None
    label: str | None = None

    def __post_init__(self) -> None:
        try:
            interval = Interval(*self.extent)
        except (TypeError, ValueError) as exc:
            raise ConfigurationError(f"AxisSpec.extent: {exc}") from exc
        object.__setattr__(self, "extent", (interval.lo, interval.hi))
        if self.arrow is not None:
            object.__setattr__(self, "arrow", ArrowPlacement(self.arrow))


def build_axes(x: AxisSpec, y: AxisSpec) -> list[Layer]:
    x0, x1 = x.extent
    y0, y1 = y.extent
    if x.arrow is None and y.arrow is None:
        layers: list[Layer] = [
            PathLayer(
                ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)),
                id="axes.frame",
                role="axes",
                clip=False,
            )
        ]
    else:
        layers = []
        for name, spec, points in (("x", x, ((x0, 0), (x1, 0))), ("y", y, ((0, y0), (0, y1)))):
            layers.append(
                PathLayer(
                    points,
                    id=f"axes.{name}",
                    role="axes",
                    stroke=Stroke(arrow=ArrowStyle.TRIANGLE) if spec.arrow else None,
                    arrow_placement=spec.arrow or ArrowPlacement.END,
                    clip=False,
                )
            )
    # Titles sit past the arrow tips: the x title to the right, the y title above.
    if x.label:
        layers.append(
            TextLayer(
                (x1, 0),
                x.label,
                id="axes.x.label",
                role="axes",
                anchor="left",
                offset=(TITLE_GAP, 0),
            )
        )
    if y.label:
        layers.append(
            TextLayer(
                (0, y1),
                y.label,
                id="axes.y.label",
                role="axes",
                anchor="bottom",
                offset=(0, TITLE_GAP),
            )
        )
    return layers


def quadrant_axes(x_max: float, y_max: float) -> list[Layer]:
    return build_axes(
        AxisSpec((0, x_max), ArrowPlacement.END), AxisSpec((0, y_max), ArrowPlacement.END)
    )


def crosshair_axes(x_range: tuple[float, float], y_range: tuple[float, float]) -> list[Layer]:
    return build_axes(
        AxisSpec(x_range, ArrowPlacement.BOTH), AxisSpec(y_range, ArrowPlacement.BOTH)
    )


def box_frame(total_x: float, total_y: float) -> list[Layer]:
    return build_axes(AxisSpec((0, total_x)), AxisSpec((0, total_y)))
