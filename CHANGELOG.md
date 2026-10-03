# Changelog

## Unreleased

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
