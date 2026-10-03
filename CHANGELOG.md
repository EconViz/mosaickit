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
