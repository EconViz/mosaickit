"""A standalone diagram without any economic domain dependency."""

from pathlib import Path

from bezierkit import CubicBezierSegment, Point

from mosaickit import (
    Canvas,
    CanvasSpec,
    Fill,
    FillLayer,
    LegendLayer,
    MarkerLayer,
    PathLayer,
    Stroke,
    TextLayer,
    quadrant_axes,
)


def build_diagram() -> Canvas:
    curve = CubicBezierSegment(Point(1, 8), Point(2, 3), Point(6, 2), Point(9, 1))
    return (
        Canvas(CanvasSpec(title="A renderer-neutral diagram"))
        .extend(quadrant_axes(10, 10))
        .add(
            FillLayer([(1, 1), (1, 7), (8, 1)], fill=Fill(color="#377EB8", opacity=0.1), z_index=-1)
        )
        .add(PathLayer(curve, stroke=Stroke(width=2), id="curve", legend="Cubic curve"))
        .add(MarkerLayer([(4, 3)], id="point", legend="Point"))
        .add(TextLayer((4, 3), "A", offset=(8, 8)))
        .add(LegendLayer())
    )


if __name__ == "__main__":
    output = Path("diagram.png")
    canvas = build_diagram()
    canvas.save(output)
    canvas.save(output.with_suffix(".tex"))
