# Changelog

All notable released changes are recorded here. Versions follow semantic versioning; evidence states
distinguish pure tests, Houdini runtime tests, authentic pixels, external models, and human review.

## 0.30.0 — 2026-08-25

### Added

- Deterministic capability catalog across 71 tools, 30 recipes, one HDA, and 17 skills, with context,
  risk, approvals, I/O, budgets, license, build, dependency, fallback, evidence, and content hash.
- Filterable `system.catalog` and no-cook `session.describe` tools.
- Pure compatibility, evidence, capability, intent-plan, handoff, and resume-plan schemas.
- Exclusive, hashed, path-confined `handoff.create`, `.inspect`, and `.resume_plan` tools; resume is
  always dry and compatibility-gated.
- Dispatcher execution context for pending approvals, active cook jobs, policy, and bridge mode.
- Hermes operator runbook and two-process `model.fractal_relic` acceptance harness.

### Hardened

- Headless session bootstrap falls back from unavailable playbar UI state to `$FSTART`/`$FEND`
  without cooking or moving the frame.
- Embedded handoff project roots and every nested checkpoint, replay, and artifact path are confined
  to dispatcher-approved roots with symlink resolution.
- Handoff and intent contracts preserve alternatives, exact feedback, blank ratings, pending human
  gates, and `winner: null`.

### Evidence

- Pure: 168 passed, 4 skipped; Ruff and `git diff --check` passed.
- Packaging: the wheel built as `houdini_creative_dev-0.30.0-py3-none-any.whl`.
- Houdini: 34 Hython integration tests passed on Apprentice 22.0.368.
- End to end: authenticated loopback bootstrap, six exact approvals, graph/data/visual pass, hashed
  handoff valid, 46 stable IDs resolved in a second Hython process, no automatic refinement.
- Pixels: authentic 640x360 Karma CPU PNG passed deterministic mechanics with no flags.
- Human aesthetic review: pending; no candidate or material winner was selected.
