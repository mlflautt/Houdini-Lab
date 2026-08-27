# Grinder Lane G003-C — Living Biome Solaris Assembly

## Mission

Create a small registered LOP composition fragment that imports all three Living Biome SOP outputs,
binds three exact Material Foundry material prims, and exposes an editable non-rendering USD stage.
The graph preserves simultaneous alternatives and never launches Karma or chooses a winner.

## Frozen execution contract

- Local root: `/Users/m1/houdini-g003-c`
- Branch: `codex/grinder-g003-c-solaris-assembly`
- Base: exact accepted SHA in `CYCLE_MANIFEST.md`
- Other-lane dependencies: none; use the frozen three SOP and material path contracts
- Merge authority: integration captain only

Stop unless the manifest is accepted, HEAD/base and cleanliness match, and frozen inputs are
complete. Read architecture, Apprentice constraints, existing World Seed/Material Foundry/Relic
Stage LOP recipes and validators, the G003 manifest, and this brief. Retrieve official Houdini 22.0
docs and run read-only exact type/parameter probes before introducing a LOP operator.

## Owned paths

- `hermes_houdini/living_biome_stage.py`
- `recipes/lop/living_biome_*.yaml`
- `tests/unit/test_living_biome_stage.py`
- `tests/fixtures/projects/g003-stage-*.json`
- `docs/living-biome-stage.md`
- `docs/grinder/receipts/G003-C.md`

Do not edit SOP files, existing skills/recipes, runtime/receipt modules, project YAML, shared
metadata, workflows, or another receipt.

## Frozen stage contract

Pure planning accepts explicit SOP paths for the three variants, exact Material Foundry material
prim paths, `/stage` parent, project-confined non-overwriting artifact paths, 1–48 timeline, stable
seed/variant IDs, and Apprentice ceilings. It emits registered `recipe.instantiate` envelopes only.

The recipe uses explicit SOP Imports into stable prim paths beneath `/World/LivingBiome`, explicit
Material Library/Assign Material bindings, fixed-order merge/comparison organization, named camera,
light, render-settings contracts, and `OUT_LIVING_BIOME_STAGE`. Camera/light/render settings are
editable staging contracts, not permission to render. Do not use selection, active pane, implicit
frame, wildcard material assignment, human Switch output, Python LOP, or arbitrary USD code.

Expose a pure validation description sufficient for integration to assert exact prims, material
bindings, contexts, stable IDs, comparison order, and no render invocation. All outputs remain
non-commercial and the optional future render ceiling is 1280×720.

## Required tests and proof

Cover deterministic plan/recipe parameters, exact variant/prim/material mapping, missing/duplicate
paths, traversal, wrong context, frame/resolution ceilings, no render call, no selector/winner, and
clean import without Houdini. Validate recipe schema. Read-only Hython probes prove exact H22 node
types/parameters only; do not mutate or save a scene.

Run targeted/full pure, Ruff, recipe validation, import, and ownership/diff checks. Record graph,
cook, USD composition, pixel, human, and downstream evidence as pending/not applicable.

## Handoff

Commit the ready receipt with public API, recipe ID/version, official-doc references, exact probes,
tests, required inputs, and integration notes. Push and open an unmerged PR. Stop on operator drift
or a missing Material Foundry contract rather than widening scope.
