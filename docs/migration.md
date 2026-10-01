# Domain-package adoption

Core provides the standalone foundation. Changes to `econ-viz` / `utility-viz`
belong in that repository and should retain its existing compatibility lifecycle.

1. Add a bounded core dependency once its release is published. During local
   integration, use a uv source override to the core checkout.
2. Replace direct artist construction in a small domain slice with factories
   returning `PathLayer`, `FillLayer`, `MarkerLayer`, and `TextLayer`. Keep economic
   calculations and contour-level selection in the domain package.
3. Define concept-local string enums such as `Budget.MAIN = "utility.budget"`,
   `Budget.COMPENSATED = "utility.budget.compensated"`. The latter inherits the
   former's theme fields through dotted fallback. Register defaults in Python.
4. Translate legacy constructor ranges into `CanvasSpec`, styles into sparse
   `StyleBundle` patches, and axis options into `AxisSpec`. `Stroke.style` in old
   code becomes core `Stroke.dash`. Config search order remains explicit path,
   `utility-viz.toml`, `econ-viz.toml`, defaults; parsing delegates to `Config.load`
   after legacy key translation.
5. Re-export `Layout`. Translate Figure construction with
   `CanvasGrid.from_layout` and Animator sweeps with `Animation.sweep`. Do not
   preserve mutable global Config in core; use explicit Config or `use_config`.
6. Compare fixed-font artist structures and normalized TikZ commands before
   changing legacy defaults. Keep the legacy implementation as a one-release
   rollback path; keep public compatibility facades throughout 2.x.
7. Migrate one vertical slice (budget, equilibrium, decomposition) first. Remove
   the domain's old Effect structure only after all its callers use generic
   arrow/text layers and its compatibility policy permits removal.

Core intentionally has no `budget`, `equilibrium`, `solve`, contour computation,
or domain compatibility aliases. Reverse imports are forbidden by import-linter.
Do not import `_RenderContext` or `_RenderPlan` from a domain package: construct
scenes through `Canvas` and consume its rendering/export API.

The compatibility foundation and first vertical slice are plan Tasks 15–16 in
the domain repository; they are not part of this core repository's implementation.
