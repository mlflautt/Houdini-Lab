# Grinder Cycle G003 — Living Biome Live Composition

- State: `PROPOSED — OWNER MOTION CHOICE AND ACCEPTANCE REQUIRED`
- Manifest version: `1.0-draft`
- Proposed on: `2026-08-26`
- Target horizon: Horizon 3 live reference composition
- Repository: `mlflautt/Houdini-Lab`
- Frozen base commit: `44727325ecb5262a613d259d6db2ff23274ed211`
- Base provenance: protected-main merge of G002 PR #22; final-main CI run `33029329282` passed
- Target runtime: Houdini Apprentice 22.0.368, Apple silicon, macOS
- Package-version intent: remain `0.35.0` during development; release decision is separate
- Motion selection: `UNSET — DO NOT DISPATCH`

## Decision and launch authority

G003 is not accepted and its prompts are inert. Before dispatch, the owner must select exactly one
motion capability from `MOTION_DECISION.md`. The orchestrator then records the exact ID/version,
candidate contract, ceilings, and approval class here, changes the state to `ACCEPTED`, and records
the owner's words. Only then may the owner use:

> Accept Grinder Cycle G003 and launch lanes A-D from 44727325.

That acceptance authorizes repository development and read-only Hython probes. It does not itself
authorize a live artist-scene edit, a full-range cook, simulation, viewport automation, Karma,
plugin installation, model call, or downstream application. The integration captain must present
the final dry run manifest and request the exact bounded graph/data action separately.

## Outcome

Turn G002's stable 15-stage dry plan into a guarded, resumable live Living Biome build. The result
must remain a readable graph: registered World Seed, Botanical Grammar, the owner-selected motion
system, Material Foundry, small adapter subgraphs, and Solaris assembly. It preserves Amber Mesa,
Verdant Rift, and Lunar Basin simultaneously, with no automatic rating, ranking, or winner.

G003 succeeds when a fresh `.hipnc` can be rebuilt in a new scene from source, each stage is bound
to the exact dry-plan/source identity, the graph and sampled data pass beneath declared ceilings,
the observer consumes real stage receipts and artifact hashes, and another agent can continue from
the saved project without hidden UI state. Pixels remain a separate optional gate.

## Non-goals

- No arbitrary Python/VEX, Python SOP, destructive artist-network replacement, implicit current
  selection/pane/frame, background execution, or unbounded retry.
- No automatic capability/adapter selection, aesthetic ranking, biome winner, motion winner,
  material winner, or silent candidate Switch choice.
- No full-range simulation, PDG child work, cache population, Karma render, plugin install, external
  model, or downstream transfer in the base G003 authorization.
- No monolithic builder that recreates skill internals. Compose registered skills and small native
  adapter recipes; Houdini performs geometry work.
- No release tag or public `v0.40.0` claim merely because the development cycle merges.

## Frozen composition invariants

- Source plan schema: `hermes.houdini.project_plan.v1`.
- Source fixture: `projects/living_biome/project.yaml`.
- Variants, in immutable presentation order: `amber-mesa`, `verdant-rift`, `lunar-basin`.
- World capability: `world.world_seed_atlas_labs@1.0.0`, with `labs_available: false` unless a
  later explicit plugin decision records exact capability evidence.
- Botanical capability: `grow.botanical_grammar@1.0.0`.
- Material capability: `lookdev.procedural_material_foundry@1.0.0`.
- Motion capability: owner-selected exact ID/version only; the G002 particle choice is a technical
  fixture and carries no aesthetic authority.
- Every capability's three explicit candidate outputs remain addressable. Composition adapters may
  bind stable candidate IDs to stable biome variant IDs, but must not consume a skill's
  human-selected output as a shortcut.
- Parent paths, contexts, stable Hermes IDs, checkpoints, outputs, frame range, seeds, budgets,
  approvals, and evidence are explicit. The current frame is restored after every allowed cook.
- Apprentice outputs are `.hipnc`/non-commercial, project-confined, non-overwriting, and no render
  exceeds 1280×720.

## Lane DAG and ownership

```text
protected-main G002 base
  +-- G003-A run governor -----------------+
  +-- G003-B SOP composition --------------+--> G003-I live integration
  +-- G003-C Solaris assembly -------------+
  +-- G003-D execution receipt/handoff ----+
```

| Lane | Owned implementation | Owned tests/docs | Must not edit |
|---|---|---|---|
| A | `hermes_houdini/project_runtime.py` | `tests/unit/test_project_runtime.py`, `docs/project-runtime.md`, `docs/grinder/receipts/G003-A.md` | recipes, skills, observer/compiler, live execution |
| B | `hermes_houdini/living_biome_sop.py`, `recipes/sop/living_biome_*.yaml` | `tests/unit/test_living_biome_sop.py`, `tests/fixtures/projects/g003-sop-*.json`, `docs/living-biome-sop.md`, `docs/grinder/receipts/G003-B.md` | LOPs, runtime governor, receipts, shared metadata |
| C | `hermes_houdini/living_biome_stage.py`, `recipes/lop/living_biome_*.yaml` | `tests/unit/test_living_biome_stage.py`, `tests/fixtures/projects/g003-stage-*.json`, `docs/living-biome-stage.md`, `docs/grinder/receipts/G003-C.md` | SOPs, runtime governor, receipts, shared metadata |
| D | `hermes_houdini/project_run_receipt.py` | `tests/unit/test_project_run_receipt.py`, `docs/project-run-receipt.md`, `docs/grinder/receipts/G003-D.md` | recipes, skills, compiler/observer, live execution |
| I | `skills/project.living_biome/*`, `projects/living_biome/*`, `tests/unit/test_living_biome_project.py`, `tests/hython/test_living_biome_project.py` | narrow registration/package exports, shared docs, `docs/grinder/receipts/G003-I.md` | lane history, automatic taste decisions, inferred evidence |

No lane imports a sibling lane. Integration alone wires the four public plain-mapping APIs.

## Frozen cross-lane interfaces

### A — run governor

Pure functions accept a G002 dry plan plus explicit runtime identity and approval records. They emit
canonical `hermes.houdini.project_run.v1` state with exact plan/source hashes, ordered stage states,
dependency readiness, risk/approval requirements, budgets, checkpoints, and
`automatic_execution: false`. `next_runnable_stage` returns zero or one stage description; it never
calls a tool, starts Houdini, grants approval, discovers a scene, or retries.

### B — SOP composition fragment

Pure planning accepts explicit registered candidate paths for world, botanical, and selected motion
outputs plus the stable biome mapping. It emits only registered `recipe.instantiate` envelopes and
named contracts beneath an explicit `/obj` parent. Native nodes perform transforms, merges, packing,
attribute tagging, and output contracts. The fragment retains all three variants and exposes
`OUT_AMBER_MESA`, `OUT_VERDANT_RIFT`, `OUT_LUNAR_BASIN`, and `OUT_BIOME_COMPARE` without a winner.

### C — Solaris fragment

Pure planning accepts the three SOP output paths and three exact Material Foundry material prims.
It emits a registered LOP recipe plan for three explicit SOP Imports, material bindings, stable
variant prim paths, camera/light/render-settings contracts, and one non-rendering `OUT_STAGE` Null.
No lane call launches Karma, changes the desktop, or silently selects a variant.

### D — run receipt

Pure functions bind the dry-plan hash, source commit/dirty state, runtime identity, exact stage
records, checkpoint/scene/artifact byte hashes, evidence rung, budgets, warnings, approvals, and
pending human fields into canonical `hermes.houdini.project_run_receipt.v1`. Missing evidence stays
pending; mismatched identities or bytes block continuation. A handoff view uses project-relative
portable paths and preserves rejected/unfinished lineage.

## Baseline live ceilings

These are upper bounds, not targets. The accepted motion choice may reduce them but may not widen
them without a manifest amendment.

| Resource | Cycle ceiling |
|---|---:|
| points per SOP variant | 300,000 |
| primitives per SOP variant | 300,000 |
| aggregate peak memory | 8 GiB |
| graph-edit time | 300 s |
| sampled data-cook time | 600 s |
| sampled frames | start, midpoint, end only |
| frame range | 1–48 |
| retained cache | 0 bytes unless separately approved |
| viewport/Karma | unapproved; optional later, max 1280×720 |

## Integration sequence and evidence gates

1. Re-audit each lane head/PR/receipt and ownership, then merge A→B→C→D with ordinary commits.
2. Wire the project skill and regenerate the dry plan. Stop on any source, catalog, adapter, build,
   license, budget, or motion-selection drift.
3. Run pure/Ruff and full Hython regression. Perform read-only operator/parameter probes against
   22.0.368; do not infer a missing node from an older build's docs.
4. Produce a no-side-effect run manifest and present its exact graph/data approvals and ceilings.
5. Only after explicit approval: create a fresh project scene, checkpoint before each coherent
   medium-risk edit, instantiate registered graphs, sample only declared frames, restore timeline,
   validate graph/data, save a new `.hipnc`, and build the run receipt.
6. Optional viewport/Karma proof requires a later independent approval and does not become human
   taste evidence. Present the three variants in stable order and ask the owner which lineage, if
   any, should continue.
7. Merge through protected main. A package tag/release is a separate decision after evidence review.

## Cycle exit gate

Required: protected-main CI, clean pure/Ruff, H22.0.368 Hython regression, exact current-build probes,
repeatable dry/run manifests, readable three-variant graph, sampled graph/data proof, hashed `.hipnc`
and continuation receipt, preserved alternatives, and blank human fields. Pixel, plugin, model,
downstream, and human gates must remain accurately pending/not applicable unless separately run.
