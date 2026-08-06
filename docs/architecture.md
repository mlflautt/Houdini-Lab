# Hermes Houdini Apprentice: Agentic Architecture and Development Guide

> Integrated source of truth for this repository. Original document:
> `Hermes_Houdini_Apprentice_Agentic_Development_Guide.md` (2026-08-06).
> This is a condensed, navigation-friendly version. The repo implements §3–§13.

**Purpose:** A reliable, creative Houdini capability for Hermes on the Apple-silicon MacBook
Pro, using Houdini Apprentice for personal, educational, non-commercial work.

**Target workstation:** M1 Max MacBook Pro, 64 GB unified memory, macOS.
**Baseline:** Houdini 22 Apple-silicon production build, pinned per project.
**License baseline:** Houdini Apprentice / Non-Commercial.

---

## 1. Executive blueprint

Treat Houdini as an executable visual programming system. The central artifact is a
**structured, readable, parameterized node graph** an artist can inspect, edit, reuse, learn
from. The recommended loop: inspect → translate intent → validate → checkpoint → build/modify
→ cook selectively → observe → critique → refine → validate/save/document → promote patterns.

First objective: a **dependable, reversible, graph-first procedural substrate** from which
increasingly sophisticated skills compose.

Houdini becomes Hermes's procedural laboratory for: generative geometry, simulation, motion,
world-building, data viz, materials, USD assembly, procedural variation/batches, render-pass
generation for downstream AI, and reusable creative systems (not one-off meshes).

## 2. Design principles
1. **Graph-first, code-second** — native nodes → composition → HDA/recipe → VEX → HOM → Python SOP → privileged code.
2. **HOM orchestrates; Houdini computes** — SOPs/VEX/DOPs/LOPs/TOPs/COPs/HDAs for work.
3. **Context is part of the type** — declare category, parent, operator type, inputs, outputs, build range.
4. **Avoid hidden UI state** — no selection/network-editor/frame/desktop dependency.
5. **Non-destructive by default** — branches, Switch, Null contracts, File Cache, Stash, bypass.
6. **Cooking is an explicit resource decision** — scope + budget always declared.
7. **Verify data AND visually** — geometry stats + viewport/flipbook/Karma.
8. **Apprentice awareness is core** — 1280×720 ceiling, non-commercial formats, no Engine, no 3rd-party renderers.

## 3. System architecture
Two-process local-first design:
- **Hermes Orchestrator** (planner, recipe selector, context resolver, policy gate, budget manager, provenance).
- **Local bridge** (outside Houdini): localhost transport, schema validation, auth, allowlists, timeouts, log aggregation.
- **Houdini package** (inside Houdini): event-loop dispatcher, graph inspector, tool/recipe registry, stable-ID service, checkpoint manager, cook/cache controller, visual observer, minimal panel.
- **Execution modes**: Interactive · Hython (tests/validation) · PDG/TOP local · Background Karma CPU (no 3rd-party renderers).

Keep transport separate from Houdini semantics (§3.1). `hrpyc` is NOT the default production
bridge (no auth, broad surface) — use the narrow authenticated bridge (§3.3).

## 4. Core components
Dispatcher (queue + bounded event-loop callback), graph inspector (compact structured info),
stable Hermes IDs (userData), registry (tools/recipes/HDAs/builds/VEX/risk), cook/cache
manager (budget + stale detection), transaction/checkpoint manager (undo group + `.hipnc`
checkpoints), visual observer (viewport/flipbook/Karma), minimal Python panel.

## 5. Command & skill model
- **Command envelope** (protocol 1.0): tool, version, args, policy, expected.
- **Structured result**: changed_nodes, cook, warnings, checkpoint, artifacts, data.
- **Tool vs recipe vs skill vs HDA** (§5.3). Skill manifest (YAML) declares id/version/contexts/
  inputs/preconditions/risk/checkpoint/cook_budget/steps/verification/outputs/rollback (§5.4).

## 6. Canonical agent loop
Understand → Inspect → Plan → Validate → Execute → Cook/observe → Critique → Refine → Finalize.

## 7. Project & graph conventions
Project layout (§7.1), `$JOB`/`$HIP` paths, top-level context containers (`HERMES_ASSET_*`,
`HERMES_STAGE_*`, `HERMES_PDG_*`, `HERMES_OUTPUT_*`), SOP Null contracts (`IN_GEO`, `OUT_GEO`,
`OUT_DEBUG`...), network boxes (INPUT/PREP/GENERATE/SIMULATE/POST/...), naming, parameter &
attribute policy, node layout, provenance.

## 8. Apprentice constraints
Non-commercial only · cannot mix into commercial pipelines · `.hipnc`/`.hdanc` · no Engine ·
no 3rd-party renderers · watermarked restricted renders · node-locked license. **Use 1280×720
as the conservative render ceiling** (§8.2). Tag every manifest with license mode (§8.3).
Design for upgrade to Indie/FX without hard-coding Apprentice behavior (§8.4).

## 9. macOS / M1 Max setup
Houdini 22 production (pin build) · Apple Silicon supported · Karma CPU baseline (no Apple-GPU
XPU) · Python 3.13 default (vendor pure-Python deps; separate venv for bridge/AI) · three-button
mouse · package JSON over `houdini.env` · VS Code + hython for tests.

## 10. Tool API (first surface)
system/license · HIP/project · read-only graph · geometry · foundational graph-edit · SOP ·
VEX · cache/cook · simulation · Solaris/USD · render/observation · PDG/TOP · HDA. Build read-only
tools before edit tools. Avoid a general "build arbitrary SOP graph" tool until mature.

## 11. Safety & permission model
Risk classes (read-only → low → medium → high → external/privileged). Approval policy for
destructive/over-budget/network/publish ops. Path allow/deny lists. Code modes (safe /
development / privileged-local). Resource guards (points/voxels/frames/substeps/samples/
resolution/time/bytes). Fail-safe behavior (§11.6).

## 12. HOM best practices
Separate pure logic from HOM · exact operator types · no selection dependency · preserve
expressions/keyframes · undo groups · careful event-loop callbacks · no Python point loops ·
no forced full-range cooks · structural error capture · userData provenance · HDAs for stable
interfaces · package files over `houdini.env` · UI optional · viewer states for mature skills ·
replayable intent logs.

## 13. Recommended plugins
Install SideFX Labs (pin build). Add MOPS only after compatibility check. Selective Orbolt.
Prioritize built-in systems (SOPs, LOPs, Karma, PDG, Copernicus, Vellum, Pyro, RBD, FLIP,
KineFX/APEX, HeightFields, MaterialX, HDAs, viewer states). Avoid third-party renderers and
unrestricted "AI assistant" plugins under Apprentice.

## 14–22. Curriculum, roadmap, backlog, testing, evaluation, docs, anti-patterns, done-definition, mandate
See the original `Hermes_Houdini_Apprentice_Agentic_Development_Guide.md` for the full text of
the creative skill curriculum (Stages 1–10), 9-sprint roadmap, skill backlog, testing strategy
(§17), creative evaluation framework (§18), learning plan (§19), anti-patterns (§20),
production-ready definition (§21), and the initialization mandate + first acceptance test (§22).
