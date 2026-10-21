# Changelog

## Unreleased

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
