# AGENTS.md — Instructions for AI Coding Agents

This repository builds an **agentic Houdini** capability: tools, recipes, HDAs, VEX
templates, and skills that let an AI agent drive SideFX Houdini (Apprentice/Indie/FX)
**graph-first** — the node graph is the primary executable artifact, not a canvas for
arbitrary pasted Python/VEX.

Read [`docs/architecture.md`](docs/architecture.md) before doing substantive work. For any creative
project or visible-output request, also read
[`docs/CREATIVE_AGENT_START_HERE.md`](docs/CREATIVE_AGENT_START_HERE.md). The principles below are
mandatory.

## Design principles (do not violate)

1. **Graph-first, code-second.** Prefer native nodes → readable node composition → versioned
   HDA/recipe → small VEX snippet → HOM/Python orchestration → Python SOP only when nothing
   else fits. Never reach for "execute arbitrary Python in Houdini" as the normal path.
2. **HOM orchestrates; Houdini computes.** Use HOM to create/connect/parameterize nodes and
   manage files. Do **not** loop over millions of points in Python — use VEX/SOPs.
3. **Context is part of the type.** A node type is meaningless without its category
   (SOP/OBJ/LOP/DOP/TOP/COP/CHOP/APEX). Declare category, parent path, exact operator type.
4. **No hidden UI state.** Tools must not depend on selection, current pane, network-editor
   path, display flag, frame, or desktop. Use absolute paths / stable Hermes IDs.
5. **Non-destructive by default.** New branch > rewrite; Switch nodes for alternatives; Null
   as named contracts; File Cache before expensive work; bypass not delete during exploration.
6. **Cooking is an explicit resource decision.** Distinguish graph edit / single-node cook /
   display-chain cook / one frame / full range / PDG cook / render. Report scope, enforce budget.
7. **Verify data AND visually.** Geometry stats + viewport capture / flipbook / Karma preview.
8. **Apprentice awareness is core.** Never assume Apprentice == commercial. Use 1280×720 as the
   conservative render ceiling. Non-commercial `.hipnc`/`.hdanc`, no Engine export, no 3rd-party
   renderers. See `docs/apprentice-constraints.md`.
9. **Stable IDs.** Tag Hermes-managed nodes with `userData` `hermes_id`/`hermes_role`/`hermes_created_by`.

## Safety & permission model

- **Risk classes:** read-only → low → medium → high → external/privileged. Require explicit
  approval for: deleting/replacing artist networks, overwriting sources, global config changes,
  plugin installs, over-budget sim/render, network access, arbitrary VEX/Python, HDA publish, any
  unclear-license op.
- **Path policy:** allow project root, approved asset roots, package logs, temp/cache dirs.
  Deny home traversal, system dirs, secrets, config folders, unrelated repos, app bundles.
- **Code modes:** *safe* (registered tools/recipes/VEX templates only) · *development* (generated
  code shown, linted, path-checked, approved) · *privileged-local* (unrestricted, disabled by
  default, never remote).
- **Bridge:** `hrpyc` is NOT the default production bridge (no auth, broad surface). Prefer the
  narrow authenticated localhost bridge in `bridge/`. Bind to `127.0.0.1` only.

## Repo conventions

- Pure-Python logic (schemas, policy, ids, registry, recipe parsing, naming, manifests) lives in
  `hermes_houdini/` and `bridge/` and **must import without Houdini present** (lazy `import hou`).
- HOM calls happen only inside functions guarded by `hou` availability; unit tests run without Houdini.
- Every skill = `skills/<id>/skill.py` + `skill.yaml` manifest (see `skills/README.md`).
- Every recipe = `recipes/<ctx>/<name>.yaml` (see `recipes/README.md`).
- `.hdanc`/`.hipnc` are binary → keep **source-of-truth** as build scripts + YAML, not committed binaries.
- Checkpoint with incremented `.hipnc` before medium/high-risk work; wrap coherent edits in
  `hou.undos.group`.
- Keep command logs replayable (tool, args, resolved node types, IDs/paths, prev/new parms, cook
  scope+metrics, artifacts, build, license, seed).

## Before writing HOM/VEX

Retrieve versioned docs for the pinned Houdini build first. Prefer official docs → vetted local
examples → third-party tutorials. Do not transcribe a tutorial into one giant script; isolate
reusable subgraphs into recipes.

## Definition of done for a skill

Narrow purpose + documented; contexts & build declared; I/O + attribute contracts; schema-validated
args; stable IDs; no UI/selection dependency; explicit risk + license; declared cook/memory budgets;
checkpoint + rollback; readable named graph; artistic controls; reproducible seed; graph/geometry/
visual validation pass; project-relative safe output paths; unit tests (pure) + `hython` integration
tests; ≥1 fixture HIP; failure modes documented; deps pinned; Apprentice restrictions visible; a human
can continue editing the result.
