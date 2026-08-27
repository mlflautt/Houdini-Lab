# Grinder Lane G003-B — Living Biome SOP Composition

## Mission

Create the small graph-first SOP composition fragment that binds explicit candidate outputs from
World Seed, Botanical Grammar, and the owner-selected motion capability into three simultaneous
Living Biome variants. Reuse registered skill graphs; do not copy their internals or consume their
human-selected Switch outputs.

## Frozen execution contract

- Local root: `/Users/m1/houdini-g003-b`
- Branch: `codex/grinder-g003-b-sop-composition`
- Base and motion choice: exact accepted values in `CYCLE_MANIFEST.md`
- Other-lane dependencies: none; consume only frozen paths/contracts
- Merge authority: integration captain only

Stop unless the manifest is accepted, the motion ID/version and three candidate outputs are frozen,
HEAD is the exact base, and the tree is clean. Read `AGENTS.md`, `docs/architecture.md`, G002 adapter
docs, the selected motion skill/recipe/docs, World Seed and Botanical source contracts, existing SOP
recipe conventions, the manifest, and this brief.

Before authoring nodes, retrieve official Houdini 22.0 docs for every new operator and run a
read-only Hython probe for exact type/parameter names. Record links and probe output in the receipt;
do not guess from an older tutorial.

## Owned paths

- `hermes_houdini/living_biome_sop.py`
- `recipes/sop/living_biome_*.yaml`
- `tests/unit/test_living_biome_sop.py`
- `tests/fixtures/projects/g003-sop-*.json`
- `docs/living-biome-sop.md`
- `docs/grinder/receipts/G003-B.md`

Do not edit existing skills/recipes, LOP files, runtime governor, execution receipts, project YAML,
registries/shared metadata, workflows, or another receipt.

## Frozen graph contract

Provide pure validation/planning plus registered recipe YAML. Inputs are explicit absolute Houdini
node paths for three world outputs, three botanical candidates, and three selected-motion candidates;
they also include stable variant bindings, parent path, seed, spacing, and resource limits. Reject
selection paths, unknown/missing/duplicate candidate IDs, contexts other than SOP, hidden current
node state, or non-finite/unbounded controls.

The recipe uses readable native nodes only: Object Merge (explicit paths), small transform/attribute
composition, Merge/Pack only where justified, named Null contracts, and a fixed-order comparison.
Every variant carries stable `variant_id`, source capability IDs/versions, seeds, and `hermes_*`
userdata. Expose exactly:

- `OUT_AMBER_MESA`
- `OUT_VERDANT_RIFT`
- `OUT_LUNAR_BASIN`
- `OUT_BIOME_COMPARE`

No candidate is display-selected as winner. Adapters must preserve source outputs and create new
branches. Geometry operations happen in SOP nodes, not Python loops. Planning returns registered
`recipe.instantiate` envelopes only and remains safe to import without Houdini.

## Required tests and proof

Pure tests cover schema, fixed order, stable IDs, exact candidate bindings, path/context rejection,
budget rejection, deterministic envelope/recipe inputs, no selector shortcut, and no arbitrary
code node. Validate recipe schema with existing loaders. Read-only Hython probes may confirm operator
and parameter availability; no live composition cook or saved scene belongs to this lane.

Run targeted/full pure, Ruff, recipe validation, clean import, and diff/ownership checks. Record all
live graph/data/pixel/human evidence as pending/not applicable.

## Handoff

Commit the ready receipt with exact public API, recipe ID/version, required paths, operator probes,
tests, and integration mapping. Push and open an unmerged component PR. Stop on a missing H22
operator or contract mismatch; do not repair an existing skill or silently choose another motion.
