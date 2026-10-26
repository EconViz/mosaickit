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
GlyphKit (`>=1.0.0b2,<2`) is installed as a required dependency for font processing.

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
  A callout leader runs from the region to one of the label box's eight anchors, never to
  an arbitrary point of an edge. The anchor is the one facing the region:

  ```
  1------2------3
  |             |
  4             5
  |             |
  6------7------8
  ```

  Take the direction from the box center to the start of the leader and round it to one of
  eight 45 degree sectors (a label right of the region gets anchor 4, one above it gets 7,
  and so on); the leader stops 2 pt short of that anchor. It is still one straight segment,
  and a `nudge` re-picks the anchor from the label's new position.
  `mosaickit.layout.leader_anchor(pole, rect)` is that rule as a pure function.
- `LegendLayer` builds legends from stable layer IDs.
- `AxisMarkLayer`, `AxisNoteLayer`, and `BraceLayer` annotate values and spans on an axis.
- `SpanBraceLayer` braces a horizontal or vertical span between two points inside the
  plot, with its label placed so it covers nothing (on a leader when there is no room).
- `GroupLayer` groups layers without adding renderer-specific state.

`AxisSpec` and `build_axes()` construct axes from the same ordinary path and text
layers. `quadrant_axes()`, `crosshair_axes()`, and `box_frame()` cover common
layouts. `CanvasSpec` owns ranges, physical size, DPI, labels, and title.

Saving to a `.tex` path writes the scene as TikZ, for a `Canvas` or a
`CanvasGrid`; pass `standalone=False` to get just the `tikzpicture`. Paths are
written as polylines unless a geometry package registers a serializer for its
curve type with `register_path_serializer`, which lets it emit native Bézier
segments without MosaicKit depending on it. Curve construction itself stays
outside MosaicKit.

Rotation annotations use the same boundary between geometry and layout. The
domain package supplies two display-space paths and a pivot, while a curve
package supplies the connector callback:

```python
from mosaickit.layout import Rect, place_rotation_marker

placed = place_rotation_marker(
    old_path,
    new_path,
    pivot,
    Rect(0, 0, width_px, height_px),
    connector,
    accepted=earlier_marker_paths,
    clearance=label_size_px,
)
```

The search begins at the shorter usable tail and moves inward until the sampled
connector fits and clears every obstacle. `extend_polyline_tail()` provides a
physical amount of visible line beyond a marker, and `tail_label_position()`
places a label's bottom-center anchor on the invisible continuation of that
tail. Their distances are display units, so callers can derive them from the
active font and stroke metrics.

Line geometry follows the same renderer-neutral boundary. `clip_segment()` and
`clip_polyline()` retain the parts inside any `Rect`; a clipped polyline returns separate
fragments when it leaves and later re-enters. `extend_chord()` adds absolute or
solved-span-relative tails, while `chord_to_rect()` continues a chord to a viewport.
For a line whose visual angle must stay fixed as panel proportions change, provide both
coordinate systems explicitly:

```python
from mosaickit.layout import Rect, line_through_display_slope

line = line_through_display_slope(
    (50, 4),
    -0.75,
    data_rect=Rect(0, 0, 100, 10),
    display_rect=Rect(0, 0, 600, 300),  # points or pixels
)
```

The returned endpoints are in data coordinates and clipped to `data_rect`.
`line_through_display_angle()` provides the same operation with a counter-clockwise angle
in degrees. `display_slope()`, `data_slope_for_display()` and `axis_span_for_display_slope()`
convert between data and on-screen slopes from axis spans and physical size, and
`centered_view(points, gap_share=...)` returns the origin and spans of a view centred on two
solved points. These functions do not read a renderer, axes, or domain model.

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
from mosaickit import StyleBundle, TextStyle, Theme

paper = Theme(
    "paper",
    {"title": StyleBundle(text=TextStyle(size=16, color="grey-900"))},
    defaults=StyleBundle(text=TextStyle(size=12)),
)
```

`TextLayer` and `TextStyle` are public. A style sets color, size, opacity, rotation, weight
and a generic font (`"sans"`, `"serif"` or `"mono"`); font files come from `TextFonts`
(see Fonts below).

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

## Math fonts

By default math text (`TextLayer(math=True)`, axis marks, and any label written as
`$...$`) goes through Matplotlib's mathtext, so letters come out in DejaVu Sans. To
set math in a font of your choice, give the configuration a `MathFont`:

```python
from mosaickit import Canvas, Config, MathFont, TextLayer, TextStyle, use_config

config = Config(math_font=MathFont("fonts/STIXTwoMath.otf"))
with use_config(config):  # or Canvas(config=config)
    canvas = Canvas().add(TextLayer((4, 3), r"u(x_1, x_2) = x_1^\alpha x_2^{1-\alpha}", math=True))
canvas.save("diagram.svg")
```

No `rc_context` is needed, and Matplotlib's global settings are untouched. The same
setting works in TOML (a relative path is read from the file's directory):

```toml
[math]
font = "fonts/STIXTwoMath.otf"
italic = true   # default: letters in the font's math italic alphabet
```

The size and color come from the label's `TextStyle`, like any other text.

- **Fonts are explicit.** `MathFont` takes a path to an OpenType font with a `MATH`
  table, such as STIX Two Math, Libertinus Math, or Fira Math. MosaicKit and GlyphKit
  never search the system for fonts, and GlyphKit's `FontSource` has no installed-name
  lookup; pass the file. A font without a `MATH` table, or a file that is not
  a font, raises `ConfigurationError` when the canvas renders.
- **Which labels.** A label whose whole text is one `$...$` span (or a `math=True` text)
  is laid out by GlyphKit and drawn from its glyph outlines, in `TextLayer`,
  `PointLabelLayer`, `RegionLabelLayer`, `AxisMarkLayer`, `AxisNoteLayer`, and brace
  labels. Placement measures the same layout it draws, so labels keep avoiding each
  other. Text that mixes plain words with `$...$`, legends, and the title keep using
  Matplotlib, as does everything when no `MathFont` is set.
- **Supported math.** GlyphKit parses a TeX-like subset: scripts, `\frac`, `\sqrt`, Greek
  letters, accents, `\left...\right`, and big operators (see GlyphKit's math grammar).
  Anything else, such as `\mathrm` or `\cdot`, raises `RenderError` naming the formula
  instead of silently changing fonts. TikZ export is unchanged.

## Scene documents

A `Scene` can be written as a versioned, JSON-compatible document and read back, so a figure can be
stored, diffed or handed to another program without Python objects.

```python
from mosaickit.document import scene_from_json, scene_to_json

text = scene_to_json(canvas.snapshot())
scene = scene_from_json(text)
```

- **Format.** `{"format": "mosaickit.scene", "version": 1, "metadata": {...}, "layers": [...]}`. Anything
  that is not a number, string, boolean or `null` is an object with a `"$"` tag naming its kind (a layer
  class, a style, a color, an enum member, a `Parameter` or an expression), and sequences are lists.
  An unbound scene keeps its parameters and expressions; a bound snapshot holds resolved numbers.
- **Strict loading.** An unknown version, tag, field or operation, a missing field, a non-finite number,
  or a value a layer rejects raises `ConfigurationError` with the path, for example
  `layers[3].anchor: ...`. Documents are limited to `MAX_NODES` values, `MAX_DEPTH` levels and
  `MAX_STRING` characters per text, so an untrusted document can be checked before anything is built.
- **Not serialized.** A layer's `model` link, and geometry that is not plain points (a layer holding a
  BezierKit curve, for example, raises `ConfigurationError` naming the layer).
- **Compatibility.** Version 1 is frozen: `tests/fixtures/scene_v1.json` must keep loading, and a scene
  read from it is written back with the same values. An optional field added later (such as
  `TextStyle.font`) is written as `null` when unused. Loading is strict about unknown fields, so a
  document written with a field this release does not know is refused. A change that is not
  additive is a new version, read alongside the old.
- **Scope.** This is data only. Diffs between documents and ways to send one belong elsewhere.

## Text fonts

Text is set in one of three generic fonts, chosen with `TextStyle.font`: `"sans"` (the default),
`"serif"` or `"mono"`. MosaicKit supplies all three, DejaVu Sans, DejaVu Serif and DejaVu Sans Mono
from the files Matplotlib installs, and GlyphKit lays them out, so a figure looks the same on every
machine and nothing searches the system for fonts.

```python
from mosaickit import Canvas, Config, TextFonts, TextLayer, TextStyle

canvas = Canvas()
canvas.add(
    TextLayer((5, 5), "Total revenue", style=TextStyle(size=12, font="serif", weight="bold"))
)
```

To use other fonts, pass the files. Each slot you give replaces that generic font; the others keep
their defaults.

```python
fonts = TextFonts(
    sans=("fonts/SourceSans3-Regular.ttf", "fonts/SourceSans3-Bold.ttf"),
    mono="fonts/JetBrainsMono-Regular.ttf",
)
canvas = Canvas(config=Config(fonts=fonts))
```

```toml
[fonts]
sans = ["fonts/SourceSans3-Regular.ttf", "fonts/SourceSans3-Bold.ttf"]
mono = ["fonts/JetBrainsMono-Regular.ttf"]
```

- **Weight.** `TextStyle.weight` is `"normal"` (400), `"bold"` (700) or an integer from 1 to 1000.
  GlyphKit uses the nearest listed face, or sets the `wght` axis of a variable font. It never makes
  a bold face up: list one, or the nearest face is used.
- **Fonts are explicit.** Paths only. A file that is not a font raises `ConfigurationError` when the
  canvas renders. The order of the files in a slot is the order a face is tried for a character the
  first lacks. A character no listed face has raises `RenderError` naming the text: the default
  fonts have no CJK glyphs, so Chinese, Japanese and Korean text needs a font file in the slot.
- **Which text.** Strings without `$...$` in `TextLayer`, labels, axis marks and notes, and brace
  labels. Math keeps using the math font, text mixed with math, legends, arrow labels and the title
  keep using Matplotlib's default font.
- **`TextStyle.family` is gone** (removed in 1.0.0). Choose a generic font with `font` and replace
  it with files through `TextFonts`.
- **`TextFonts(paths)`** from 0.9.0 still works: the first argument is the `sans` slot, and
  `[fonts] files` is another name for `sans`.

## Moving single labels from `econ-viz.toml`

A label can be moved without touching the Python that draws the figure. In the shared part of
`econ-viz.toml` (top level, outside any package table) name the figure by its output file's stem
and the label by its layer id:

```toml
[figure.tax_welfare.label."market.welfare.dwl.label"]
top = "12pt"
right = "8pt"
```

- **Keys.** `top`, `bottom`, `left`, `right` are lengths: a number of points or a string in `pt`,
  `mm`, `cm` or `in` (`em` is rejected: the file has no font size). Opposite sides combine, as in
  `nudge_from()`. Quote ids that contain dots, and stems too (`[figure."fig.v2".label.x]`).
- **When.** `Canvas.save(path)` and `CanvasGrid.save(path)` (also `.tex`) apply the overrides of
  `Path(path).stem` to the labels whose layer id matches: point, region and text labels by their
  own id, braces by the brace id or by `<id>.label`, the id of their label in the SVG. `render()`,
  `show()` and `MatplotlibResult.save()` never apply them, and nothing happens until a config read
  from the file is activated with `Config.use()` (or `econ_toml.use()`), or
  `econ_toml.activate_figure_overrides(econ_toml.figure_labels(data))` is called.
- **Replace, not add.** An override replaces the label's own `nudge`, including one a theme or a
  group default set earlier. An empty table cancels that nudge. Leaders follow, as with any nudge.
- **Forgiving and strict.** Ids no layer has are ignored (a figure may change); malformed values
  raise `ConfigurationError` naming the file and table when the file is read.
- **Reading back.** `econ_toml.figure_overrides()` returns `{stem: {id: Nudge}}` for the active
  overrides, `figure_overrides(stem)` those of one figure; `clear_figure_overrides()` drops them.
- **Identifying labels in the SVG.** Every label is drawn in an element whose `id` is its layer id
  (a brace's label: `<id>.label`; a callout's leader: `<id>.leader`).

## Grids and parameters

```python
from mosaickit import Canvas, CanvasGrid, GridSpacing, Parameter, TextLayer

position = Parameter("position", value_type=float)
template = Canvas().add(TextLayer((position, 5), "moving"))
values = position.values([1.0, 3.0, 5.0])

CanvasGrid.sweep(
    template,
    values,
    cols=3,
    spacing=GridSpacing(column_gap=0.2, row_gap=0.15, outer=0.04),
).save("sweep.svg")
```

`CanvasGrid` accepts flat canvases, nested rows, `None` cells, and
`Span(canvas, rows=..., cols=...)`. A flat list infers a roughly square grid;
explicit `rows` and `cols` may leave trailing cells empty.
`GridSpacing` controls renderer-neutral gaps: `column_gap` and `row_gap` are
fractions of one cell, while `outer` is a symmetric fraction of the whole grid.
Omitted fields retain each renderer's existing default, so `CanvasGrid(cells)`
continues to produce the same layout. Pass it as `CanvasGrid(cells, spacing=...)`;
`sweep` and `from_layout` accept it too. Matplotlib fits the grid inside the fixed
figure (`outer` shrinks the axes), while TikZ keeps cells at their natural size and
adds `outer` around them. Under Matplotlib the spacing is applied after the cells are drawn
(as if by `subplots_adjust` on the rendered figure), so labels and links keep their place
relative to their panel. `grid.figure_size` and `mosaickit.rendering.matplotlib.grid_axes_size(grid, cell)` return
the figure and per-cell axes size in inches for sizing text or aspect ratios.

Parameters and expressions support arithmetic, ordered comparisons, partial
binding, and stable structural equality.

### Migrating from 0.9

1.0.0 removes what 0.6.0 deprecated:

- `Animation`, `Animation.sweep()` and the Matplotlib playback helper. Use KineticKit for
  animation; install it separately, MosaicKit does not depend on it. `CanvasGrid.sweep()` and
  `canvas.bind()` still draw one frame per value.
- `TextStyle.family`. Use `TextStyle(font="serif")` with `Config(fonts=TextFonts(serif=[...]))`.
  `TextStyle` now takes `color, size, weight, opacity, rotation, font`, so pass them by name.
  A version 1 scene document that holds `"family": null` still loads; a name is refused.

## Theory diagrams

`mosaickit.diagram` declares a textbook derivation figure without hand-assembling layers. It is
domain-neutral: roles are plain strings your theme resolves, label offsets come from an optional
callback, and every number is a keyword with a documented default.

```python
from mosaickit import GridSpacing, Nudge
from mosaickit.diagram import Diagram, link_points, stack
from mosaickit.layout import centered_view

view = centered_view([(8, 3), (5, 5)], gap_share=0.5)  # shifted-origin window
top = Diagram(
    view=view,
    x_label="$Y$",
    y_label="$i$",
    origin_label="0",
    rising_names_upper_right=True,
    nudge=lambda layer: None,
)
top.line("is", [(9, 3), (5, 5)], tail=0.2, role="curve.primary", label="IS")
top.curve("lm", [(6, 3), (10, 6)], label="LM")  # name placed clear of lines
top.point("A", (8, 3), "$A$").drop("A", x="$Y_0$", y="$i_0$")  # dashed guides + axis marks
top.arrow("shift", "A", (6, 3), label="$\\Delta$")  # movement arrow
bottom = Diagram(6, 6, x_label="$Y$", y_label="$p$").point("A", (3, 2), "$A$")
grid = stack([top, bottom], link_points(0, 1, ["A"]), spacing=GridSpacing(row_gap=0.2))
grid.save("derivation.png")
```

- `Diagram(x_max, y_max | view=, x_label=, y_label=, origin_label=, title=, width=, height=,
  theme=, config=, nudge=, id_prefix=, headroom=, axes_role=, rising_names_upper_right=,
  name_order=, plot_share=, font_size=)` is one panel; `.canvas()` builds the `Canvas`.
- `.curve(name, points, role=, label=, side=, floor=, trim=)` and
  `.line(name, points, tail=, ...)` (the chord through the first and last point, `tail` of its
  length longer at each end). Names go to the first free side of `name_order` (collision-aware,
  using `mosaickit.layout` obstacles); `rising_names_upper_right` puts the name of a rising curve
  upper-right first; `side=` forces one.
- `.point(name, at, label, role=, nudge=)`, `.axis_mark(axis, value, label, name=)`,
  `.guide(start, end, name=)`, `.drop(point, x=, y=)`, `.arrow(name, start, end, label)`. Points
  are referred to by name or `(x, y)`; with a `view`, coordinates stay in data units and
  `Diagram.at(ref)` gives the shifted panel coordinates a `GridLink` needs.
- `stack(panels, links, cols=1, spacing=GridSpacing(...))` builds the `CanvasGrid`;
  `link_points(upper, lower, names, role=)` declares a `PointLink` per shared point name.
- `nudge(layer) -> Nudge | None` is added to the layer's own nudge for every label layer.
  `indexed("$Y$", 1)` and `primed("$A$")` build subscripted and primed symbols.

## Placing labels

`mosaickit.layout.labels` is one placer for curve names, point labels and tick labels. A
`Label` is a box of fixed size with an anchor and a preferred side order; `Obstacle`s are
lines, markers and boxes. `place_labels` chooses every position together, so the result does not
depend on the order you list labels in:

```python
from mosaickit.layout import Rect
from mosaickit.layout.labels import Label, LabelOptions, Obstacle, place_labels

labels = [Label("p0", end0, size0, owner="p0"), Label("p1", end1, size1, owner="p1")]
obstacles = [Obstacle.polyline(path0, owner="p0"), Obstacle.polyline(path1, owner="p1")]
result = place_labels(labels, obstacles, Rect(0, 0, width, height), LabelOptions(clearance=4.0))
for placed in result.placements:  # box, side, offset, leader, text_anchor
    ...
for warning in result.warnings:  # label_id, reason: no label is silently overlapped
    ...
```

Every box keeps its label's size (the placer has no font size to change), lies inside the
bounds, keeps `clearance` from every line, marker and box, `label_gap` from other labels, and
sits next to its own anchor: the first free preferred side, else widening rings, else a ring
beyond `leader_after` joined to the anchor by a leader line. A label that sits nearer another
label's anchor than its own is rejected unless it has a leader. Tick labels use
`spread="stack"`: they stagger outward in rows and/or flip to the opposite side
(`LabelOptions.tick_strategy`) instead of overlapping. When a label has no free position its
`Placement.ok` is `False` and a `PlacementWarning` (`no-free-position`, `conflict` or
`search-budget`) says so. Every distance and weight is a documented field of the frozen
`LabelOptions`; the search is deterministic.

`mosaickit.label_scene.place_scene_labels` does it from a canvas snapshot in one call: layers
become obstacles, labels are the `TextLayer`s you name (anchor = their own `position`), tick
labels and extra boxes such as axis titles join the same scene, and the replacement text layers
(and leader `PathLayer`s with a configurable role) come back. Pass it a size function:
`mosaickit.rendering.matplotlib.text_measurer(size, ...)` measures real text in the configured
fonts, `mosaickit.diagram.estimate_text_size` estimates when no renderer is available.

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

Each render or grid job owns its cache. Pass an explicit
`RenderCache` to reuse work across jobs. Non-hashable models bypass caching and
emit one warning per model type and cache.

## Scope

MosaicKit owns domain-neutral scene composition, styles, themes, parameter
binding, grid layout, renderer contracts, and static output. GlyphKit owns font
processing; KineticKit owns animation. Domain semantics belong to
the packages that build on it. Mathematical curve construction and native TikZ
Bézier segments belong to geometry packages such as BezierKit, which plug into
the scene-level TikZ export through a path serializer.

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
