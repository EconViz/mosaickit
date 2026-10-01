# mosaickit

Domain-neutral scenes, styles, and renderers for two-dimensional diagrams.
Python 3.10–3.13. Geometry comes from BezierKit; no economic package is required.

## Development

```sh
uv sync --locked
uv run pre-commit install
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run lint-imports
uv build
```

The lockfile pins all development dependencies. BezierKit is currently pinned to
commit `db1e66fd13749df56b6f50221d149d81a4c0adc9` (0.5.0rc1): it was not available
on the configured package index at implementation time. The same Git reference is
included in wheel metadata so installing the wheel does not require a local
sibling checkout. Replace this with a bounded registry dependency when published.

## A standalone diagram

```python
from bezierkit import CubicBezierSegment, Point
from mosaickit import Canvas, PathLayer, Stroke, quadrant_axes

curve = CubicBezierSegment(Point(1, 8), Point(2, 3), Point(6, 2), Point(9, 1))
canvas = Canvas().extend(quadrant_axes(10, 10))
canvas.add(PathLayer(curve, stroke=Stroke(color="#984EA3", width=2)))
canvas.save("diagram.svg")
canvas.save("diagram.tex")
```

`Canvas.add/extend/remove/clear` are fluent builder operations. `snapshot()` returns
an immutable `Scene`; `copy()` and `bind()` preserve the original builder. Public
layers contain no Matplotlib artists. Importing core does not import Matplotlib.
`CanvasSpec` validates finite increasing ranges, positive physical sizes in inches,
and integer DPI in `[1, 1200]`. `Interval` provides the shared range validation.

`PathLayer`, `FillLayer`, `MarkerLayer`, `TextLayer`, `ArrowLayer`, `LegendLayer`,
and grouping-only `GroupLayer` are the scene primitives. `AxisSpec` and
`build_axes()` assemble ordinary path/text layers. Use the `quadrant_axes`,
`crosshair_axes`, or `box_frame` presets for common layouts. Legend entries are
layer IDs; labelled visible layers are included when entries are omitted.

## Themes and configuration

```python
from mosaickit import Config, Stroke, StyleBundle, Theme, use_config

theme = Theme("paper", {"utility.budget": StyleBundle(stroke=Stroke(color="#984EA3"))})
with use_config(Config(theme=theme)):
    canvas = Canvas()
```

Style fields set to `None` inherit. Falsey values such as `opacity=0`, `width=0`,
and `LegendStyle(visible=False)` are explicit overrides. Precedence is layer style,
canvas role override, Config role override, theme, then primitive defaults.
Theme lookup walks dotted parents and then the layer's fallback category.
Themes defensively copy mappings and cannot be mutated through `roles`.

Domain roles registered through `ThemeRegistry.register_roles` must be dotted.
Use one `(str, Enum)` per domain concept and `RolePack` dataclasses with
`expand_roles` for typed theme authoring. Core never imports these domain types.

```toml
[canvas]
x_range = [0, 20]
dpi = 150

[styles."utility.budget".stroke]
color = "#984EA3"
width = 2
dash = "dashed"
```

Load with `Config.load(path)`. Unknown keys produce source-aware errors. Runtime
defaults use `contextvars`; explicit constructor arguments take precedence.
Configuration discovery and legacy TOML translation belong to domain packages.

## Grids, binding, and animation

```python
from mosaickit import Animation, CanvasGrid, Parameter, Span, TextLayer

p = Parameter("position", value_type=float)
template = Canvas().add(TextLayer((p, 5), "moving"))
grid = CanvasGrid.sweep(template, p.values([1.0, 3.0, 5.0]), cols=3)
grid.save("sweep.png")
Animation.sweep(template, p.values([1.0, 3.0, 5.0]), fps=2).save("sweep.gif")
```

Nested rows accept `Span(canvas, rows=..., cols=...)` and `None` empty cells.
Cells occupied by a preceding row span are skipped automatically. Flat lists infer
a roughly square shape; explicit rows/cols may leave trailing empty cells.
`CanvasGrid.from_layout` implements the legacy Layout presets through the same
placement algorithm, including the two irregular three-canvas layouts.

Expressions support arithmetic, ordered comparisons, partial binding, and stable
structural equality/hash. Use `expression.equals(value)` for an evaluated equality
predicate; `==` compares tree structure. Supply `value_type` when runtime type
checking is required. Parameter values and constants must be hashable.

`Animation.frames()` yields backend-neutral scenes. GIF uses Pillow; MP4 requires
ffmpeg. Interactive `rendering.matplotlib.animation.play()` requires Matplotlib.

## Rendering contracts

`canvas.render()` returns a result with `figure`, `axes`, `show`, `save`, and `close`
for Matplotlib. Close results when finished. `canvas.save()` closes its temporary
result automatically and returns all paths written. Save PNG/PDF/SVG with
Matplotlib or TEX/PGF with TikZ. Renderer modules load lazily. Both preserve native
cubic segments without fixed-count resampling.

TikZ supports standalone and fragment output (`fragment=True`), coordinate scale
(`tikz_scale=...`), and precision. Geometry serialization delegates to BezierKit's
public `export.tikz.to_tikz`. Separate-data mode raises `NotImplementedError` until
BezierKit provides `to_tikz_separate`. Fragment consumers must load `arrows.meta`,
`patterns`, and the `plotmarks` PGF library. Plain text is escaped; `math=True`
labels are intentional raw TeX.

`Scene`, layers, styles, themes, and the public `Renderer` protocol form the API.
Render contexts and plans remain private while the built-in backends evolve.
Each render/save/grid/animation job owns its cache; an explicit `RenderCache`
can be reused across jobs. Non-hashable models warn once per type per cache and
bypass caching without blocking rendering.

See [migration guidance](docs/migration.md) for domain-package adoption.
