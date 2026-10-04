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
- `RegionLabelLayer` names a filled region (inside it, or as a callout), and
  `PointLabelLayer` names a point with text placed right beside it. Both are
  placed after everything else is drawn so they cover no line, marker, filled
  region, or other text; a `LayoutWarning` names any label that cannot avoid
  everything.
- `LegendLayer` builds legends from stable layer IDs.
- `AxisMarkLayer`, `AxisNoteLayer`, and `BraceLayer` annotate values and spans on an axis.
- `SpanBraceLayer` braces a horizontal or vertical span between two points inside the
  plot, with its label placed so it covers nothing (on a leader when there is no room).
- `GroupLayer` groups layers without adding renderer-specific state.

`AxisSpec` and `build_axes()` construct axes from the same ordinary path and text
layers. `quadrant_axes()`, `crosshair_axes()`, and `box_frame()` cover common
layouts. `CanvasSpec` owns ranges, physical size, DPI, labels, and title.

Curve construction and TikZ export intentionally live outside MosaicKit. Domain
packages can call a geometry package such as BezierKit directly, then pass the
resulting coordinates or renderer-specific output to their own export pipeline.

## Axis marks, notes, and braces

```python
from mosaickit import AxisMarkLayer, AxisNoteLayer, BraceLayer, Canvas, quadrant_axes

canvas = Canvas().extend(quadrant_axes(10, 10))
for value, symbol, note in [(7, "a_1", "Upper\nvalue"), (5, "a_0", "Lower\nvalue")]:
    canvas.add(AxisMarkLayer("y", value, symbol, math=True))
    canvas.add(AxisNoteLayer("y", value, note))
canvas.add(BraceLayer("y", 5, 7, "Span", side="outside"))
```

The y axis is the plot's left edge and the x axis its bottom edge; the space
outside them is the gutter. Columns run outward from the axis: marks, then
outside braces, then notes, each as wide as its widest text. Marks and notes are
spread along the axis so none overlap, keeping their order and moving as little
as possible. An `"inside"` brace sits just inside the plot and its label is
placed so it covers no line, point, region, or text. Notes use the `axes.note`
role, which the default theme sets smaller and lighter than marks.

Saving grows the canvas just enough to include text drawn past its edges and
never crops; pass `expand=False` to `save()` to keep the exact `CanvasSpec`
size. Axis titles from `build_axes()` sit past the arrow tips: the x title to the
right, the y title above.

## Styles and themes

Set values shared by every role with `defaults`. Individual roles and layer
styles can still override them:

```python
paper = Theme(
    "paper",
    {
        "title": StyleBundle(text=TextStyle(family="Noto Serif TC")),
    },
    defaults=StyleBundle(text=TextStyle(family="Noto Sans TC")),
)
```

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

### Colors by name

Style `color` and `edge_color` fields take a `Color`, a `"#hex"` string, or a
palette name such as `"blue"`. Names stay names in themes and styles; they are
looked up in the active palette (`Config.palette`, default `DEFAULT_PALETTE`)
when a canvas renders, so renderers only ever receive concrete colors. The
built-in `default` theme names its colors (`primary` is `"blue"`, `secondary`
is `"red"`, `accent` is `"teal"`, neutrals are the `grey-*` names), so changing
a color once in the palette recolors every role that names it:

```python
from mosaickit import (
    DEFAULT_PALETTE,
    Canvas,
    Config,
    Palette,
    Stroke,
    StyleBundle,
    Theme,
    use_config,
)
from mosaickit.themes import default

palette = Palette("brand", {**DEFAULT_PALETTE.colors, "blue": "#0072B2", "accent": "#984EA3"})

# A domain package can name colors in its theme without knowing the palette.
mypkg = Theme(
    "mypkg",
    {
        **default.roles,
        "mypkg.line": StyleBundle(stroke=Stroke(color="blue", width=2)),
        "mypkg.boundary": StyleBundle(stroke=Stroke(color="accent")),
    },
)

with use_config(Config(theme=mypkg, palette=palette)):
    canvas = Canvas()  # primary and mypkg.line draw in #0072B2
```

A name the palette does not define raises `ConfigurationError` at render time,
naming the role, the style field, and the palette. A Python `Palette` replaces
the default palette, so start from `DEFAULT_PALETTE.colors` (as above) to keep
the names the built-in theme uses.

Domain packages register dotted role names through `ThemeRegistry`. Typed
`RolePack` dataclasses and `expand_roles()` let those packages author themes
without making MosaicKit import their domain types.

Configuration can also be loaded from TOML:

```toml
[canvas]
x_range = [0, 20]
dpi = 150

[palette]
blue = "#0072B2"     # override a default color
accent = "#984EA3"   # add a new name

[styles."mypkg.boundary".stroke]
color = "accent"     # a palette name or a "#hex" value
width = 2
dash = "dashed"

[styles."mypkg.line".stroke]
color = "blue"
```

The `[palette]` table layers named hex colors over `DEFAULT_PALETTE`, and the
loaded palette is available as `config.palette`. Overriding `blue` there
recolors the built-in `primary` role and any theme or style that names `blue`,
with no styles needed. Style `color` and `edge_color` values accept palette
names as well as hex; an unknown name raises `ConfigurationError` naming the
file and key when the file is loaded.

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
