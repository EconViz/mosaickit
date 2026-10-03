# Changelog

## Unreleased

- TOML config accepts a `[palette]` table that defines or overrides named
  colors (`accent = "#984EA3"`) on top of `DEFAULT_PALETTE`.
- Style `color` and `edge_color` values in TOML accept palette names
  (`color = "accent"`) as well as hex. Names resolve against the config's
  palette at load time; unknown names raise `ConfigurationError` naming the
  file and key.
- `Config` carries the palette: `Config(palette=...)` in Python, defaulting to
  `DEFAULT_PALETTE`. Behavior without a palette is unchanged.

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
