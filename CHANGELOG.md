# Changelog

## Unreleased

## 1.0.0rc15 — 2026-10-26

- New `mosaickit.layout.labels`: one global label placer (#87). `place_labels(labels, obstacles, bounds, options)` places curve names, point labels and tick labels together: fixed-size boxes (the font size is never changed), inside the bounds, clear of every line, marker and box by a named clearance, never on another label, each beside its own anchor. It tries the preferred sides, then widening rings, then a displaced position with a leader line, and searches for the cheapest conflict-free assignment (most constrained first, branch and bound, deterministic). A label with no free position is returned with `ok=False` and a structured `PlacementWarning`. Tick labels stagger in rows or flip to the opposite side (`tick_strategy`). Every number is a documented field of the frozen `LabelOptions`.
- New `mosaickit.label_scene.place_scene_labels`: the same engine from a canvas snapshot (curves, arrows, markers, texts, tick labels and fixed boxes in one scene), returning replacement `TextLayer`s and leader `PathLayer`s. New `mosaickit.rendering.matplotlib.text_measurer` measures real text extents in the configured fonts.
- `Diagram` keeps its own name placement for now: the global engine may pick other sides than the greedy first-free one, so outputs would change.
- Faster typesetting with identical output: the ink box of a label is now built from a per-glyph cache instead of solving the Bezier extrema of the whole path, and `TextTypesetter` loads a generic font slot (sans, serif, mono) when a string first uses it unless you gave files for it, which still load up front (#89).

## 1.0.0rc14 — 2026-10-26

- `estimate_text_size`, and so the `Diagram` name placement, sizes stacked TeX: `\frac` and `\dfrac` put the numerator over the denominator, `\left`/`\right` delimiters are as tall as what they enclose, and `^`/`_` arguments are smaller and raise the line. A label such as `$LM\,\left(\frac{M}{p_1}\right)$` is no longer estimated at one line. The factors are the named `TextSizeFactors` (`DEFAULT_TEXT_SIZE_FACTORS`, `factors=` argument); commands in `strip_commands` still count for nothing (#84).
- Internal: `mosaickit.econ_toml` and `mosaickit.diagram.builder` are now packages of smaller
  modules, and a test keeps every source file at 450 lines or fewer (#82). Every public name and
  import path is unchanged.

## 1.0.0rc13 — 2026-10-26

- `Diagram` takes `name_gap`, `name_diagonal` (share of the gap used on a diagonal side) and a
  `text_size(label, font_size)` estimator, so downstream packages can match their own placement;
  the defaults reproduce the previous behaviour exactly (#79). New public
  `mosaickit.diagram.estimate_text_size`, which can leave TeX commands such as `\left` and
  `\frac` out of the width (`TEX_LAYOUT_COMMANDS`), and `Diagram.tail_label`, a text at a fixed
  point offset from the end of a curve.

## 1.0.0rc12 — 2026-10-26

- New `mosaickit.diagram`: a small declarative builder for theory diagrams (#75). `Diagram` declares
  arrowed axes with symbol titles and an optional origin label, an optional `centered_view` for
  shifted origins, `curve`/`line` with direct names placed clear of every line, point and name
  (with a rising-curves-upper-right option), named marked points, dashed `guide`/`drop` lines to
  axis marks, and `arrow`. `stack()` with `link_points()` stacks panels into a `CanvasGrid` with
  `GridLink`s between named points and a `GridSpacing`. A `nudge` callback and role strings keep
  configuration and themes in the caller.
- Fix `CanvasGrid` spacing under Matplotlib: `GridSpacing` is now applied after the cells are
  drawn, like a `subplots_adjust` on the rendered figure, instead of before. Point labels,
  leaders and gutters are placed against Matplotlib's default axes and then re-spaced with the
  figure, so a grid with spacing renders pixel-identically to one adjusted after rendering and
  downstream packages can drop their own post-render renderers. Grids without spacing are
  unchanged. (#74)

## 1.0.0rc11 — 2026-10-26

- Add renderer-neutral `GridSpacing` for `CanvasGrid`. Column and row gaps are
  proportional to one cell and the symmetric outer margin is proportional to
  the whole grid. Matplotlib and TikZ exports honor explicit spacing while
  omitted values preserve their previous renderer defaults. New
  `CanvasGrid.figure_size` and `mosaickit.rendering.matplotlib.grid_axes_size` report the rendered
  figure and per-cell axes size in inches. (#71)
- Add renderer-neutral line geometry (#71) to `mosaickit.layout`: segment and
  fragmented-polyline clipping, absolute or relative chord extension, viewport-wide chords,
  and lines constructed from a requested display-space slope or angle while accounting for
  data and panel aspect ratios. Also `clip_polyline(points, x_range, y_range)`,
  `extend_line_through()`, `display_slope()` / `data_slope_for_display()` /
  `axis_span_for_display_slope()` and `centered_view()` for views centred on two solved points.

## 1.0.0rc10 — 2026-10-25

- New display-space rotation layout helpers in `mosaickit.layout`:
  `place_rotation_marker()` searches from the usable path tails inward, respects panel bounds and
  obstacles, and keeps multiple accepted markers apart; `extend_polyline_tail()` adds physical
  tail clearance; and `tail_label_position()` puts a label's bottom-center anchor on the continued
  tail tangent. The connector geometry is injected, preserving MosaicKit's independence from
  curve and domain packages.

## 1.0.0rc9 — 2026-10-24

- Callout leaders (`RegionLabelLayer` callouts, and the callout a `BraceLayer`/`SpanBraceLayer`
  label falls back to) now end at one of the label box's eight anchors, the four corners and
  four edge midpoints, instead of the nearest point anywhere along an edge. The anchor is the
  one facing the start of the leader: the direction from the box center to the start is rounded
  to one of eight 45 degree sectors, so a label to the right of its region gets the left-edge
  midpoint, one above it the bottom-edge midpoint, and so on. The leader still stops 2 pt short
  and is still one straight segment (`<id>.leader` in the SVG, same attributes). The same rule
  runs when the callout position is searched, so the search ranks the leaders that get drawn,
  and again after a `nudge` or an `econ-viz.toml` override moves the label.
- New `mosaickit.layout.leader_anchor(pole, rect)`: the rule as a pure function.
- Figures without a callout are unchanged; with one, only the end of the leader moves.

## 1.0.0rc8 — 2026-10-24

- Fix: the label of an axis-gutter `BraceLayer` (`side="outside"`, e.g. tax-wedge, trade and
  policy braces) ignored its `nudge`. It now moves by the nudge, in points, like every other
  label, and so does the `[figure.<stem>.label."<id>"]` override of `econ-viz.toml` (by `<id>` or
  `<id>.label`). Only the label moves: the brace outline stays. Axis mark and note labels have no
  `nudge` and stay where they are spread. Without a nudge the output is unchanged.

## 1.0.0rc7 — 2026-10-24

- Per-figure label overrides in the shared part of `econ-viz.toml`:
  `[figure.<stem>.label."<layer id>"]` with `top`, `bottom`, `left`, `right` lengths (points, `pt`,
  `mm`, `cm`, `in`; `em` is rejected) moves one label of the figure saved as `<stem>.<ext>`, so a
  tool can store "this label was dragged" without editing the user's Python. `Canvas.save()` and
  `CanvasGrid.save()` apply them (also to `.tex`); an override replaces the label's own `nudge`
  (it wins over theme and group defaults, an empty table cancels it), the leader follows, ids no
  layer has are ignored, and braces also match `<id>.label`. `render()` and
  `MatplotlibResult.save()` never apply them, and without overrides the output is unchanged.
- `Config.use()` of any package config read from a file activates that file's overrides;
  `Config.reset()` drops what that package activated. `econ_toml.figure_labels(data)` parses them,
  `figure_overrides(stem=None)` reads the active ones, `activate_figure_overrides()` and
  `clear_figure_overrides()` set and drop them, `SharedSettings.figures` and `Config.figure_labels`
  carry them. Malformed values raise `ConfigurationError` naming the file and table.
- `figure` is a shared top-level table (`econ_toml.SHARED_SECTIONS`), not an unknown key.

## 1.0.0rc6 — 2026-10-23

- Packages no longer parse `econ-viz.toml` themselves. A package declares an
  `econ_toml.Schema`: its built-in themes (`base`), the keys of its own table with the attribute
  each sets (`color`, `number`, `positive`, `length`, `boolean`, `string`, `choice`, `path`,
  `transform`; `length` takes points or strings such as `"2mm"` and `"0.1in"`), tables with free
  names such as `[utility.stroke.<name>]` (`pattern`), and which shared settings it uses.
  mosaickit reads the file, checks every value, resolves relative paths against the file's
  directory and reports mistakes with the file and table they are in, suggesting the closest key
  for a typo or listing the valid keys when none is close: `econ-viz.toml: [principle.color]
  unknown key 'demnad'; did you mean 'demand'?`. Unknown top-level keys are an error; other
  packages' tables are skipped.
- `Schema.config_class()` gives the package's `Config` class (`load`, `discover`, `from_dict`,
  `use`, `reset`, `active`, and the built object's attributes), and `Schema.template()` writes the
  package's commented section.
- utility-viz settings left at the top level (`[color] ic`, `[stroke.*]`, ...) are read as if they
  were under `[utility]`, with one warning naming the new place; `[utility]` wins when both set a
  key.
- `econ_toml.register()`, `registered()` and `load()` build every registered package from one file;
  `econ_toml.use()` loads and activates every installed package that declares an `econviz.config`
  entry point.
- `utility` is now a package table like the others (`econ_toml.PACKAGES`, also `PACKAGE_TABLES`).
- Shared themes: `mosaickit.themes` defines the themes every EconViz package offers (`manual`,
  `default`, `colorblind`, `monochrome`, `nord`, `paper`, `presentation`) as colours for named roles
  (`ink`, `primary`, `secondary`, `constraint`, `accent`, the region fills, ...) plus line, marker and
  label scales. A package maps its own elements to roles once, so one theme name looks the same in
  every package. `get_tokens()`, `list_shared_themes()`, `SHARED_THEMES`, `ThemeTokens`, `ROLES`.
- Label nudges: point, region, brace and text labels take `nudge=Nudge(dx, dy)` in points, applied
  after automatic placement, so a single label can be moved a little without giving up placement;
  leaders follow the moved label and later labels avoid it. `parse_length()` reads `"10pt"`,
  `"0.5em"`, `"2mm"`, `"0.1in"`, and `nudge_from(top=, bottom=, left=, right=)` builds a nudge.
  Without a nudge the output is unchanged.

## 1.0.0rc5 — 2026-10-23

- `mosaickit.econ_toml` reads the sections of `econ-viz.toml` that every EconViz package shares:
  `base`, `[font]`, `[fonts]` and the `background`, `axis` and `label` colours, with relative
  paths resolved against the file. Packages other than utility-viz keep their own settings in
  one table each (`[principle]`, `[micro]`, `[macro]`, `[trade]`, `[dsge]`, `[game]`), listed in
  `econ_toml.PACKAGE_TABLES`, and skip the others'.

## 1.0.0rc4 — 2026-10-23

- Parsed fonts are shared across symbolic links: the text and math typesetter caches are keyed
  by the fonts' real paths, so the same files reached through different links are parsed once.
- A title set in the configured fonts puts its baseline where Matplotlib puts a title's, the title
  padding above the axes. In 1.0.0rc3 its bottom sat there, about 5 pt higher than before.

## 1.0.0rc3 — 2026-10-22

- Titles and text that mixes words with `$...$` math are set in the configured text fonts.
  With `Config.fonts` given, the canvas title is laid out by GlyphKit like every text layer,
  centred above the axes at Matplotlib's title padding, and text Matplotlib draws uses your file
  for the style's generic font; before, both used Matplotlib's own fonts, so Chinese came out as
  boxes. Without `Config.fonts` the output is byte for byte unchanged.

## 1.0.0rc2 — 2026-10-22

- Faster drawing with identical output. Label placement tests a candidate against 32 or more
  segments or polygon edges on arrays instead of one at a time, plain numeric point lists are
  validated as one array, and plain values skip the parameter search. Matplotlib's data-limit
  bookkeeping, which MosaicKit never reads because it sets both axis limits, is skipped while a
  scene is drawn. A cache keyed by the font properties and the relevant `rcParams` sits in front of
  Matplotlib's mathtext parser while a scene is drawn and saved; Matplotlib's own cache is keyed by
  parser instance and never hits across figures. Both are scoped to one draw or save and restore
  Matplotlib afterwards. SVG output is byte for byte unchanged (compared on 14 figures and with
  tests of each kernel against the loop it replaces).

## 1.0.0rc1 — 2026-10-21

- Remove `Animation`, `Animation.sweep()` and the Matplotlib animation helper (deprecated in 0.6.0).
  Use KineticKit for animation. `CanvasGrid.sweep()` and `canvas.bind()` are unchanged.
- Remove `TextStyle.family` (deprecated in 0.6.0). Choose `font` and replace it with files through
  `TextFonts`. `TextStyle` is now `TextStyle(color, size, weight, opacity, rotation, font)`: pass
  fields by name. Matplotlib-drawn text (titles, legends, text mixed with `$...$`) uses
  Matplotlib's default font, as it did for a style without `family`.
- A version 1 scene document that has `"family": null` still loads; one that names a family is
  refused. Documents written now omit the field.

## 0.9.2 — 2026-10-21

- TikZ export sets the generic font of a text style: `\sffamily` for `"sans"` (the default),
  `\rmfamily` for `"serif"` and `\ttfamily` for `"mono"`. A style that still sets the deprecated
  `family` keeps deciding when it names a known family.

## 0.9.1 — 2026-10-21

- Math is spaced and set by GlyphKit 1.0.0b3, which now follows TeX's layout rules: fractions, scripts,
  limits, radicals, delimiters and accents, with TeX's spacing around operators, relations and
  punctuation. MosaicKit no longer adds spaces around operators or converts the minus sign itself.
  Formulas that used to fail now work, for example `\le`, `\cdot`, `\infty`, `\partial`,
  `\mathrm{...}`, `\sin` and the whole Greek alphabet. Requires `glyphkit>=1.0.0b3,<2`.

- Text is set in three generic fonts, chosen with the new `TextStyle.font` (`"sans"` by default,
  `"serif"`, `"mono"`) and laid out by GlyphKit. MosaicKit supplies DejaVu Sans, DejaVu Serif and
  DejaVu Sans Mono from the files Matplotlib installs, so every font has a default and no
  configuration is needed.
- `TextFonts(sans=..., serif=..., mono=...)` replaces any of the three with your font files and
  leaves the others at the defaults. Its first argument is `sans`, so `TextFonts(paths)` from 0.9.0
  still means the same; TOML `[fonts]` takes `sans`, `serif` and `mono`, with `files` kept as another
  name for `sans`.
- Behaviour change: default text is now drawn from glyph outlines instead of by Matplotlib (in SVG
  and PDF as paths), and a character the font lacks, such as a CJK character, raises `RenderError`
  naming the text instead of drawing a missing-glyph box.
- A style that sets the deprecated `TextStyle.family` keeps its Matplotlib path.
- Version 1 of the scene document gains the optional `TextStyle.font` field, written as `null` when
  unused.

## 0.9.0 — 2026-10-21

- Add `mosaickit.document`: `scene_to_dict`/`scene_to_json` and `scene_from_dict`/`scene_from_json`
  write and read a `Scene` as a versioned (version 1) JSON-compatible document, with strict loading
  and limits on size, nesting and text length.
- Add `TextFonts` and `Config(fonts=...)` (TOML: `[fonts] files = [...]`) to set plain text in
  caller-chosen fonts through GlyphKit, the way `MathFont` does for math. Weight is chosen by
  GlyphKit from the listed faces; without `TextFonts` text is unchanged.
- `TextStyle.weight` is no longer deprecated. It takes `"normal"`, `"bold"` or an integer from 1 to
  1000, and other values raise `ConfigurationError`. Only `TextStyle.family` stays deprecated.

## 0.8.0 — 2026-10-20

- `DashStyle` accepts the short forms `-`, `--`, `:` and `-.`; `ArrowStyle` accepts
  the Matplotlib spellings `->` (open) and `-|>` (triangle) and gains `SIMPLE` as
  another name for `OPEN`. A caller that exposes its own line and arrow style enums
  can now use these two directly.

## 0.7.0 — 2026-10-19

- Add `MathFont` and `Config(math_font=...)` (TOML: `[math] font = "..."`) to set
  math text in a caller-chosen OpenType math font through GlyphKit. When set, labels
  that are a single `$...$` span or `math=True` text (`TextLayer`, `PointLabelLayer`,
  `RegionLabelLayer`, axis marks and notes, brace labels) are laid out from the font's
  `MATH` table and drawn from glyph outlines, with italic letters and spaced operators;
  placement measures the same layout. This replaces wrapping saves in
  `matplotlib.rc_context({"mathtext.fontset": ...})`. With no `MathFont`, rendering is
  unchanged and still uses mathtext. A font without a `MATH` table raises
  `ConfigurationError`; a formula GlyphKit cannot parse raises `RenderError`.

## 0.6.0 — 2026-10-19

- Add scene-owned TikZ export for `Canvas` and `CanvasGrid`, including a path
  serializer registry that geometry packages can extend without becoming a
  MosaicKit dependency.
- Require `glyphkit>=1.0.0b2,<2` for font processing. `TextLayer` and
  `TextStyle` remain public; color, size, opacity, and rotation remain supported.
- Deprecate `TextStyle.family` and `TextStyle.weight`: explicitly supplying
  either emits one caller-facing `DeprecationWarning` directing users to
  GlyphKit. Legacy font values and Matplotlib output remain unchanged, and
  internal theme setup, style copying, and rendering do not repeat warnings.
- Deprecate `Animation` and `Animation.sweep()` with one construction-time
  warning directing users to KineticKit. Both public import paths, frames,
  GIF/MP4 saving, and the existing playback helper continue to work. KineticKit
  is not a MosaicKit dependency. The next release may remove these animation
  APIs/helpers and the legacy family/weight font path; see the README migration
  guidance before upgrading.
- A theme can define a `defaults` `StyleBundle`. These values sit above
  MosaicKit's primitive defaults and below semantic roles and layer overrides,
  so applications can set shared text size and color while retaining per-role
  and per-layer typography.

## 0.5.1 — 2026-10-03

- Markers are drawn whole: a marker centred on the plot edge (such as a point on
  an axis) is no longer cut in half, and a marker centred outside the plot is
  left out (it was clipped away before).

## 0.5.0 — 2026-10-03

- Add `GridLink(start_cell, start, end_cell, end, role=..., stroke=...)` and
  `CanvasGrid(..., links=...)`: a straight line from a point in one cell to a
  point in another, each in its own cell's data coordinates, drawn across the
  gaps between cells. It is styled by `role` in the start cell's theme, with
  `stroke` on top.
- `ArrowLayer` honors a dashed, dotted or dash-dot stroke: the shaft takes the
  dash and the heads stay solid. It was drawn solid before.

## 0.4.0 — 2026-10-03

- Add `SpanBraceLayer(start, end, label, side)`: a curly brace between two points
  inside the plot (horizontal span: `side` `"above"`/`"below"`; vertical span:
  `"left"`/`"right"`). Its label sits past the tip, covering nothing; when there
  is no room there it moves out on a leader.
- Inside axis-brace labels gain the same leader fallback when nothing past the
  tip is free (previously they warned and overlapped).

## 0.3.2 — 2026-10-03

- Point labels treat a region as theirs only when the point is strictly inside
  it; a point on a region's edge (such as a vertex) keeps its label out of the
  region, as before 0.3.1.

## 0.3.1 — 2026-10-03

- Point labels may sit inside a filled region that contains their point (for
  example a point inside a shaded area); other regions are still avoided.

## 0.3.0 — 2026-10-03

- Themes and styles refer to colors by palette name (`Stroke(color="blue")`).
  Names resolve against the active palette (`Config.palette`) when the render
  plan is built, so changing a color once in the palette, in Python or in a
  TOML `[palette]` table, recolors every role that names it. Renderers still
  receive only concrete colors.
- The built-in `default` theme and primitive defaults name their colors
  (`blue`, `red`, `teal`, `white`, and the `grey-*` ramp) instead of holding
  copies of `DEFAULT_PALETTE` values. Rendered output with the default palette
  is unchanged.
- An unknown color name raises `ConfigurationError` naming the role, field,
  and palette. A custom `Palette` must define the names its theme uses; build
  it from `DEFAULT_PALETTE.colors` to keep the built-in names.
- TOML config accepts a `[palette]` table that defines or overrides named
  colors (`accent = "#984EA3"`) on top of `DEFAULT_PALETTE`.
- Style `color` and `edge_color` values in TOML accept palette names
  (`color = "accent"`) as well as hex. Unknown names raise
  `ConfigurationError` naming the file and key when the file is loaded.
- `Config` carries the palette: `Config(palette=...)` in Python, defaulting to
  `DEFAULT_PALETTE`. Behavior without a palette is unchanged.
- Add `PointLabelLayer(point, text)`, which places its text right beside a point
  so it covers nothing. It tries 16 directions around the point at a few small
  gaps from the point's marker edge (nearest first, upper-right preferred) and
  takes the closest position that stays inside the axes and touches no line,
  marker, filled region, or other text. The point's own marker is never covered.
  When no position is free it takes the one with fewest overlaps and emits a
  `LayoutWarning` naming the layer.
- Point labels are placed before region labels, so region callouts avoid them.
- Add `place_point_label` to `mosaickit.layout`. `Placement.leader` may be
  `None` (labels drawn without a leader).
- Label text is measured with its `TextStyle.rotation`, so rotated region labels
  are placed using their rotated extent.
- Add `AxisMarkLayer` (a symbol next to an axis at a value), `AxisNoteLayer` (an
  explanation further out), and `BraceLayer` (a curly brace over a span, with an
  optional label). They work on both the x and y axis.
- Text outside an axis is laid out in columns running outward: marks, then
  outside braces (one column per lane of overlapping braces), then notes. Marks
  and notes are spread along the axis so none overlap. An inside brace's label is
  placed so it covers no line, point, region, or text, and emits `LayoutWarning`
  when no such spot exists.
- Add pure layout modules: `mosaickit.layout.geometry.brace_outline`,
  `mosaickit.layout.stack1d` (`spread`, `assign_lanes`), `mosaickit.layout.gutter`,
  and `mosaickit.layout.placement.place_beside`.
- Add the `axes.note` role to the default theme (9 pt, `grey-600`).
- Add `SaveOptions.expand` (default `True`). Visible change: saving grows the
  canvas to include anything drawn past its edges. It never crops, so a diagram
  that fits keeps its `CanvasSpec` size. Pass `expand=False` for the old behaviour.
- Visible change: `build_axes`, `quadrant_axes`, and `crosshair_axes` place axis
  titles past the arrow tips (the x title to the right, the y title above)
  instead of centred on the tip, where they covered the arrowhead.

## 0.2.0 — 2026-10-03

- `TextLayer.anchor` accepts `top-left`, `top-right`, `bottom-left`, and
  `bottom-right`. The anchor names the corner of the text box placed at
  `position`. Existing anchors behave as before.
- Arrowheads are no longer clipped to the axes, so axis arrows whose tips sit on
  the boundary draw both wings.
- Axis presets (`build_axes`, `quadrant_axes`, `crosshair_axes`) draw filled
  triangle arrowheads by default instead of open chevrons. Pass a stroke with
  `ArrowStyle.OPEN` to keep the old look.
- `PathLayer` accepts `clip` (default `True`). Axis presets set `clip=False`
  so axis lines on the plot boundary keep their full stroke width instead of
  losing the outer half.
- Path arrowheads no longer redraw a solid shaft over the last 15% of the path,
  so dashed arrows stay dashed and axis lines keep a uniform width.
- Add `RegionLabelLayer`, which names a filled region. With `placement="auto"`
  the label goes inside the region when it fits (trying `short_text` second),
  otherwise it becomes a callout: a thin leader and unboxed text placed so it
  does not cover any line, point, filled region, or other text.
- Add the pure-geometry `mosaickit.layout` package that makes those decisions.
- Add `LayoutWarning`, emitted when no callout position avoids every obstacle.
- Add `Palette`, a named color table, and `DEFAULT_PALETTE`: a grey ramp
  (`grey-900` … `grey-100`, `white`) plus `blue` `#01A2D9`, `red` `#E3120B`,
  and `teal` `#00887D`.
- The default theme now takes every color from `DEFAULT_PALETTE`. Visible
  change: `primary`, `secondary`, and `accent` become the palette's blue, red,
  and teal (previously ColorBrewer Set1 blue, red, and purple). Neutral greys
  are unchanged.
- Layers declare `style_slots` (which field holds their explicit style for each
  style slot), and Matplotlib drawing is driven by a per-type registry. Add
  `register_builder` and `register_pass` in `mosaickit.rendering.matplotlib`
  so other packages can add layer types without changing MosaicKit.
- `themes.resolve` accepts `overrides`, applied in order after the theme.
- Region-label callouts avoid everything drawn on the axes, including layers
  drawn by registered third-party builders.
- Built-in renderers are loaded by name on first use; the core no longer
  imports the Matplotlib backend.

## 0.1.1 — 2026-10-01

- Add verified project links for the homepage, source repository, issue tracker,
  changelog, and release notes to the package metadata shown on PyPI.

## 0.1.0 — 2026-10-01

- Add immutable viewport, styles, namespaced themes, scenes, and generic layers.
- Add Canvas, spanning CanvasGrid, parameter expressions, and Animation.
- Add Matplotlib rendering with job-scoped caches.
- Add strict TOML config and context-local defaults.
- Add uv dependency management, pytest, Ruff, mypy, import-linter, and pre-commit.
- Keep curve mathematics and TikZ export outside MosaicKit so it remains an
  independent layer-composition package.
- Add the MosaicKit brand asset and package overview README.
