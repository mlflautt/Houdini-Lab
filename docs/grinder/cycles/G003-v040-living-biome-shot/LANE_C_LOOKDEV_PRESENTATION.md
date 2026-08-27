# Grinder Lane G003-C — Lookdev, Lighting, Camera, and Presentation

## Mission

Create the registered Solaris composition that presents all three animated biome outputs with exact
Material Foundry candidates, readable light/camera controls, and stable comparison framing. Build an
editable non-rendering USD stage contract; do not launch Karma or choose a preferred look.

## Frozen execution contract

- Worktree: `/Users/m1/houdini-g003-c`
- Branch: `codex/grinder-g003-c-lookdev-presentation`
- Base: exact protected-main accepted SHA in the launch record
- Inputs: frozen Lane B output/material contracts as plain data; no sibling source import
- Merge authority: integration captain only

Stop unless Gate V/H1 and the launch record are complete, HEAD/base are exact, inputs are frozen,
and the tree is clean. Read architecture, Apprentice constraints, accepted packet, Material Foundry,
World Seed and existing Solaris/lookdev recipes, official H22.0.368 docs, and this brief.

## Owned paths

- `hermes_houdini/living_biome_lookdev.py`
- `recipes/lop/living_biome_lookdev_*.yaml`
- `tests/unit/test_living_biome_lookdev.py`
- `tests/fixtures/projects/g003-lookdev-*.json`
- `docs/living-biome-lookdev.md`
- `docs/grinder/receipts/G003-C.md`

Do not edit SOP/review modules, existing skills/recipes, project YAML, shared metadata, workflows,
another receipt, live scenes, or rendered artifacts.

## Required contract

Pure planning accepts the three explicit animated SOP paths, exact Material Foundry prims, `/stage`
parent, stable variants, timeline, camera/framing controls, key/fill/world lighting controls,
atmosphere/exposure parameters, project-confined output templates, and Apprentice ceilings. Emit
registered recipe-instantiation envelopes only.

The LOP recipe creates explicit SOP Imports below `/World/LivingBiome`, exact material bindings,
fixed-order comparison organization, named camera/light/render-settings contracts, and
`OUT_LIVING_BIOME_STAGE`. Provide editable controls for focal length, camera pose/target, subject
spacing, crop-safe margin, key direction/size/intensity, fill ratio, world exposure, and material
assignment. Defaults are neutral starting hypotheses, not aesthetic rankings.

Reject wildcard bindings, selection/active-pane state, Python LOP/arbitrary USD, implicit frame,
output overwrite, XPU/third-party delegate, resolution above 1280×720, and any render invocation.

## Verification and handoff

Test exact prim/material/variant mapping, stable order/IDs, deterministic envelopes, framing and
light controls, traversal/overwrite/frame/resolution rejection, no render call, no selector/winner,
and clean import. Validate recipes and run targeted/full pure, Ruff, diff/ownership, wheel/package,
and read-only current-build node/parameter probes. Live USD, pixels, and taste remain pending.

Commit owned paths and factual receipt, push, and open an unmerged PR. Report base/head, API, recipe,
official-doc/probe evidence, tests, exact integration inputs, and pending execution gates.
