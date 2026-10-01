"""A standalone diagram without any economic domain dependency."""

from pathlib import Path

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
    curve = [(1, 8), (2, 5), (4, 3), (7, 1.5), (9, 1)]
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
