# mosaickit

<p align="center">
  <img src="https://raw.githubusercontent.com/EconViz/mosaickit/main/assets/banner.svg" alt="mosaickit" width="480">
</p>

<p align="center">
  <a href="https://pypi.org/project/mosaickit/"><img alt="PyPI" src="https://img.shields.io/pypi/v/mosaickit?style=flat-square&color=181818&labelColor=f3f3f3&cacheSeconds=300"></a>
  <a href="https://pypi.org/project/mosaickit/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/mosaickit?style=flat-square&color=181818&labelColor=f3f3f3"></a>
  <a href="https://opensource.org/licenses/MIT"><img alt="License" src="https://img.shields.io/badge/License-MIT-181818?style=flat-square&color=181818&labelColor=f3f3f3"></a>
  <a href="https://github.com/EconViz/mosaickit/actions/workflows/test.yml"><img alt="Tests" src="https://img.shields.io/github/actions/workflow/status/EconViz/mosaickit/test.yml?branch=main&style=flat-square&label=tests&color=181818&labelColor=f3f3f3"></a>
</p>

A domain-neutral toolkit for assembling two-dimensional diagrams from reusable
scenes, layers, styles, parameters, and renderers.

Domain libraries define their own models and semantic roles; MosaicKit composes
their visual layers and renders the result. It knows nothing about any domain
and does not depend on a model package or a curve-fitting library.

## Installation

Add MosaicKit to a project with [uv](https://docs.astral.sh/uv/):

```bash
uv add mosaickit
```

A plain `pip install mosaickit` also works. MosaicKit supports Python 3.10–3.13.

## Python API

```python
from mosaickit import (
    Canvas,
    Fill,
    FillLayer,
    MarkerLayer,
    PathLayer,
    Stroke,
    TextLayer,
    quadrant_axes,
)

canvas = Canvas().extend(quadrant_axes(10, 10))
canvas.add(
    FillLayer(
        [(1, 1), (1, 7), (8, 1)],
        fill=Fill(color="#377EB8", opacity=0.12),
        z_index=-1,
    )
)
canvas.add(
    PathLayer(
        [(1, 8), (2, 5), (4, 3), (7, 1.5), (9, 1)],
        stroke=Stroke(color="#984EA3", width=2),
        id="curve",
    )
)
canvas.add(MarkerLayer([(4, 3)], id="point"))
canvas.add(TextLayer((4, 3), "A", offset=(8, 8)))
canvas.save("diagram.svg")
```

`Canvas.add()`, `extend()`, `remove()`, and `clear()` are fluent builder
operations. `snapshot()` returns an immutable `Scene`; `copy()` and `bind()`
produce a new canvas without changing the original. Public layers never contain
Matplotlib artists, and importing `mosaickit` does not import Matplotlib.

## Scenes and layers

The scene graph is deliberately small:

- `PathLayer` joins ordered finite `(x, y)` coordinates with straight segments.
- `FillLayer` describes filled regions.
- `MarkerLayer`, `TextLayer`, and `ArrowLayer` add annotations.
- `LegendLayer` builds legends from stable layer IDs.
- `GroupLayer` groups layers without adding renderer-specific state.

`AxisSpec` and `build_axes()` construct axes from the same ordinary path and text
layers. `quadrant_axes()`, `crosshair_axes()`, and `box_frame()` cover common
layouts. `CanvasSpec` owns ranges, physical size, DPI, labels, and title.

Curve construction and TikZ export intentionally live outside MosaicKit. Domain
packages can call a geometry package such as BezierKit directly, then pass the
resulting coordinates or renderer-specific output to their own export pipeline.

## Styles and themes

```python
from mosaickit import Config, Stroke, StyleBundle, Theme, use_config

paper = Theme(
    "paper",
    {"mypkg.boundary": StyleBundle(stroke=Stroke(color="#984EA3", width=2))},
)

with use_config(Config(theme=paper)):
    canvas = Canvas()
```

Style resolution proceeds from layer style to canvas role override, configuration
role override, theme, and finally primitive defaults. A field set to `None`
inherits; falsey values such as `opacity=0`, `width=0`, and
`LegendStyle(visible=False)` remain explicit overrides.

Domain packages register dotted role names through `ThemeRegistry`. Typed
`RolePack` dataclasses and `expand_roles()` let those packages author themes
without making MosaicKit import their domain types.

Configuration can also be loaded from TOML:

```toml
[canvas]
x_range = [0, 20]
dpi = 150

[styles."mypkg.boundary".stroke]
color = "#984EA3"
width = 2
dash = "dashed"
```

Use `Config.load(path)` to validate it. Runtime defaults are isolated with
`contextvars`, while explicit constructor arguments always take precedence.

## Grids, parameters, and animation

```python
from mosaickit import Animation, Canvas, CanvasGrid, Parameter, TextLayer

position = Parameter("position", value_type=float)
template = Canvas().add(TextLayer((position, 5), "moving"))
values = position.values([1.0, 3.0, 5.0])

CanvasGrid.sweep(template, values, cols=3).save("sweep.svg")
Animation.sweep(template, values, fps=2).save("sweep.gif")
```

`CanvasGrid` accepts flat canvases, nested rows, `None` cells, and
`Span(canvas, rows=..., cols=...)`. A flat list infers a roughly square grid;
explicit `rows` and `cols` may leave trailing cells empty.

Parameters and expressions support arithmetic, ordered comparisons, partial
binding, and stable structural equality. `Animation.frames()` yields
backend-neutral scenes. GIF output uses Pillow; MP4 output requires ffmpeg.

## Rendering

PNG, SVG, and PDF use the built-in Matplotlib renderer:

```python
result = canvas.render()
try:
    result.show()
finally:
    result.close()
```

`canvas.save()` closes its temporary render result automatically. The public
`Renderer` protocol and `RendererRegistry` allow other backends without placing
backend state in the scene graph. Render plans and contexts remain private while
the built-in backends evolve.

Each render, grid, or animation job owns its cache. Pass an explicit
`RenderCache` to reuse work across jobs. Non-hashable models bypass caching and
emit one warning per model type and cache.

## Scope

MosaicKit owns domain-neutral scene composition, styles, themes, parameter
binding, grid layout, animation frames, renderer contracts, and static/animated
output. Domain semantics belong to the packages that build on it. Mathematical curve construction and native TikZ path generation
belong to geometry packages such as BezierKit.

## Development

```bash
uv sync --locked
uv run pre-commit install
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run lint-imports
uv build
```

The lockfile pins all development dependencies.
