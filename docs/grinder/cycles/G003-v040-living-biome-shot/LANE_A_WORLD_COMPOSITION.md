# Grinder Lane G003-A — World and Spatial Composition

## Mission

Create the graph-first SOP composition contract for three simultaneous Living Biome worlds. Compose
registered World Seed and Botanical Grammar outputs into editable spatial hierarchies with explicit
negative space, scale, density, and motion-anchor controls. Do not add motion, materials, lighting,
rendering, or a winner.

## Frozen execution contract

- Worktree: `/Users/m1/houdini-g003-a`
- Branch: `codex/grinder-g003-a-world-composition`
- Base: exact protected-main accepted SHA in the launch record
- Other-lane dependencies: none; consume only frozen existing capability contracts
- Merge authority: integration captain only

Stop unless Gate V passed, H1 contains the owner's exact continuation, the launch record is frozen,
HEAD is the exact base, and the tree is clean. Read the root instructions, architecture, accepted
manifest, launch record, World Seed/Botanical contracts, existing SOP recipe conventions, and this
brief before editing.

## Owned paths

- `hermes_houdini/living_biome_world.py`
- `recipes/sop/living_biome_world_*.yaml`
- `tests/unit/test_living_biome_world.py`
- `tests/fixtures/projects/g003-world-*.json`
- `docs/living-biome-world.md`
- `docs/grinder/receipts/G003-A.md`

Do not edit motion/LOP/review modules, existing skills or recipes, project YAML, registries, shared
metadata, workflows, another receipt, or live artifacts.

## Required contract

Provide pure validation/planning plus registered native recipe YAML. Inputs name all three explicit
World Seed outputs, all three Botanical Grammar candidates, stable biome bindings, `/obj` parent,
seeds, scale, spacing, density, clearance, clustering, focal-zone, and resource ceilings. Reject
selection paths, missing/duplicate candidates, wrong contexts, traversal, non-finite controls,
hidden current state, and unbounded counts.

Expose stable, separately editable contracts:

- `OUT_AMBER_MESA_WORLD`
- `OUT_VERDANT_RIFT_WORLD`
- `OUT_LUNAR_BASIN_WORLD`
- `OUT_WORLD_COMPARE`
- one named motion-anchor contract per biome

Use native SOP composition, explicit Object Merge paths, attributes, transforms, packing/merging only
where justified, named Nulls, readable network boxes, stable IDs, and fixed presentation order.
Geometry work remains in nodes, not Python loops. Controls expose macro silhouette, distribution,
scale hierarchy, focal zone, negative space, and botanical density without claiming aesthetically
good defaults.

## Verification and handoff

Test deterministic envelopes, stable IDs, fixed order, candidate/path/context rejection, resource
ceilings, no selector shortcut, no arbitrary code, and clean import without Houdini. Validate recipe
schemas and run targeted/full pure tests, Ruff, diff/ownership checks, and read-only H22.0.368
operator probes for every new node type. Live graph/data/pixels/human review remain pending here.

Commit only owned paths, complete the factual receipt, push, and open an unmerged component PR.
Report exact base/head, API, recipe IDs, tests, probes, deviations, and integration inputs.
