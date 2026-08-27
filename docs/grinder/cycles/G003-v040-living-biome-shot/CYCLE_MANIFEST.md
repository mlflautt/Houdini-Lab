# Grinder Cycle G003 — Creative-First Living Biome

- State: `PROPOSED — OWNER ACCEPTANCE AND LIVE AUDITION AUTHORITY REQUIRED`
- Manifest version: `2.0-creative-first-draft`
- Proposed on: `2026-08-26`
- Target horizon: Horizon 3 visible reference composition
- Repository: `mlflautt/Houdini-Lab`
- Base selector: protected-main commit carrying this manifest version; resolve and record its exact
  full SHA in the launch record before creating worktrees
- Target runtime: Houdini Apprentice 22.0.368, Apple silicon, macOS
- Package-version intent: remain `0.35.0` during development; release decision is separate
- Motion selection: `UNSET UNTIL AUTHENTIC THREE-WAY VISUAL AUDITION`

## Why this amendment exists

G003 must produce work the owner can see and creatively judge. The former plan could complete a
live graph/data build while leaving pixels optional and required the owner to choose a motion
language from prose. That ordering did not serve the creative purpose of Houdini Lab.

This cycle therefore begins with a small serial visual audition using three already registered
motion capabilities. The owner chooses a continuation only after reviewing authentic motion. The
parallel implementation lanes then build the Living Biome around that evidence, and the integrated
cycle ends with a visible animated comparison and at least one owner-directed revision.

## Authority boundaries

Acceptance of this cycle authorizes repository development and read-only Houdini probes. It does
not authorize a graph mutation, cook, viewport capture, Karma render, file cache, plugin install,
external model, or downstream application.

The first execution request must name the exact visual-audition action and ceilings in
`VISUAL_AUDITION.md`. After that bounded action is approved and its artifacts are reviewed, the
owner may record one motion continuation in `MOTION_DECISION.md`. Parallel lanes remain inert until
both the audition receipt and the owner's exact continuation words exist.

No approval may be inferred from a prior cycle or widened from one evidence rung to another.

## Creative outcome

Build a readable, animated Living Biome composition from registered World Seed, Botanical Grammar,
the owner-selected motion lineage, Material Foundry, small native adapters, and Solaris. Preserve
Amber Mesa, Verdant Rift, and Lunar Basin simultaneously. Produce authentic visual and temporal
evidence in stable order so the owner can critique form, rhythm, material, light, atmosphere, and
camera without any technical metric becoming a taste score.

G003 succeeds only when:

1. the three motion languages have authentic, comparable audition artifacts;
2. the owner has explicitly selected or declined a continuation after seeing them;
3. a fresh `.hipnc` rebuilds from source into a readable three-biome graph;
4. graph and sampled data pass beneath declared ceilings;
5. authentic pixels and motion evidence show the integrated result;
6. at least one exact owner critique is translated into a bounded revision with before/after
   lineage; and
7. another agent can resume from the project specification, scene, artifacts, and creative handoff
   without hidden UI state.

## Creative review invariants

- Alternatives remain equal-status until the owner acts. Stable presentation order is always
  Particle Calligraphy, Differential Growth, Kinetic Instances for the audition, then Amber Mesa,
  Verdant Rift, Lunar Basin for the integrated comparison.
- `selected_for_continuation`, `human_rating`, `winner`, and `why` stay null until populated from
  the owner's exact words after viewing exact artifact hashes.
- Mechanical visual analysis may reject blank, duplicate, corrupt, cropped, or badly exposed proof.
  It may not rank beauty, originality, mood, usefulness, or preference.
- Rejected and superseded attempts are retained with lineage. A revision never overwrites the
  artifact it is meant to improve.
- Still images cannot prove motion. Every motion claim binds a time range, sampled frames, and an
  authentic sequence or flipbook.

## Frozen project inputs

- Source plan schema: `hermes.houdini.project_plan.v1`.
- Source fixture: `projects/living_biome/project.yaml`.
- Biome order: `amber-mesa`, `verdant-rift`, `lunar-basin`.
- World: `world.world_seed_atlas_labs@1.0.0`, native fallback unless a later plugin decision records
  exact SideFX Labs evidence.
- Botanical: `grow.botanical_grammar@1.0.0`.
- Material: `lookdev.procedural_material_foundry@1.0.0`.
- Audition motions, all required and none preselected:
  `motion.particle_calligraphy@1.0.0`, `generate.differential_growth@1.0.0`, and
  `motion.kinetic_reliquary@1.1.0` native-only.
- Integrated motion: exactly one owner-selected audition lineage, or a separately amended
  composition if the owner explicitly requests a hybrid after review.
- Every capability's explicit candidates remain addressable; no skill's human-selected Switch
  output may be consumed as a shortcut.

## Cycle sequence

```text
accepted manifest
  -> V: serial three-way visual audition
  -> H1: owner reviews exact artifacts and selects/declines continuation
  -> A: world and spatial composition --------+
  -> B: selected motion and temporal design ---+--> I: live integrated composition
  -> C: material, light, camera, presentation -+
  -> D: review, critique, continuation --------+
  -> H2: owner critiques integrated comparison
  -> R1: one bounded revision and before/after review
  -> protected-main integration and separate release decision
```

The audition and integrated scene are serialized because they mutate Houdini projects and produce
shared visual artifacts. Lanes A-D develop isolated recipes, planners, validators, and review
contracts in parallel after H1.

## Lane ownership

| Lane | Creative responsibility | Owned implementation | Owned docs/tests |
|---|---|---|---|
| A | world form, botanical distribution, spatial hierarchy, three-biome composition | `hermes_houdini/living_biome_world.py`, `recipes/sop/living_biome_world_*.yaml` | matching unit fixtures/docs and `G003-A.md` |
| B | selected motion integration, timing, rhythm, temporal sampling | `hermes_houdini/living_biome_motion.py`, `recipes/sop/living_biome_motion_*.yaml` | matching unit fixtures/docs and `G003-B.md` |
| C | materials, lighting, atmosphere, camera, Solaris presentation | `hermes_houdini/living_biome_lookdev.py`, `recipes/lop/living_biome_lookdev_*.yaml` | matching unit fixtures/docs and `G003-C.md` |
| D | artifact comparison, exact feedback binding, revision hypotheses, portable creative handoff | `hermes_houdini/creative_review.py` | matching unit fixtures/docs and `G003-D.md` |
| I | serial audition/integration execution, project skill, scene, shared verification and receipt | `skills/project.living_biome/*`, `projects/living_biome/*`, narrow shared wiring | integration tests/docs and `G003-I.md` |

Exact paths, exclusions, public APIs, tests, and stop conditions live in each lane brief. No lane
imports a sibling lane. Integration alone wires public plain-mapping APIs.

## Resource ceilings

These are upper bounds, not targets. Any widening requires a manifest amendment and fresh approval.

| Resource | Visual audition | Integrated Living Biome |
|---|---:|---:|
| scenes | 3 new non-overwriting `.hipnc` | 1 new scene plus revisions |
| timeline | frames 1–24 | frames 1–48 |
| motion frames delivered | 12 evenly sampled frames per study | at least 12 evenly sampled frames |
| resolution | 640×360 | 768×432 default; 1280×720 hard ceiling |
| Karma | CPU only, 16 samples maximum | CPU only, 32 samples maximum |
| render time | 20 minutes aggregate | 30 minutes per approved comparison/revision |
| points/primitives | capability ceiling, never widened | 300,000 per biome variant |
| aggregate peak memory | 4 GiB | 8 GiB |
| retained cache | 0 bytes | 0 bytes unless separately approved |
| output bytes | 1 GiB aggregate | 2 GiB per approved review round |

The operator must stop rather than silently reduce fidelity or substitute generated/mock pixels if
the bounded runtime cannot produce authentic evidence.

## Required artifact ladder

### Gate V — motion audition

- three project-confined `.hipnc` scenes or one scene with three explicitly addressable branches;
- three labeled 12-frame sequences and playable previews;
- one stable-order contact sheet;
- graph snapshots or graph manifests for each method;
- mechanics reports proving nonblank, nonduplicate temporal evidence;
- live-byte hashes, runtime/build/license, exact seeds, parameters, frame sampling, and failures.

### Gate I — integrated composition

- readable three-biome `.hipnc` and graph manifest;
- three individual beauty frames plus one stable-order comparison;
- one authentic motion preview showing all three lineages or three synchronized previews;
- graph/data/USD/material/camera/light validation;
- no automatic winner and all unreviewed human fields null.

### Gate R1 — refinement

- verbatim user critique bound to reviewed artifact hashes and candidate IDs;
- bounded revision plan naming graph/parameter/timing/material/light/camera hypotheses;
- new non-overwriting scene/artifacts with before/after presentation;
- continuation handoff stating what was liked, disliked, rejected, changed, and not yet judged.

## Non-goals

- No arbitrary Python/VEX, Python SOP, destructive artist-network replacement, hidden selection,
  active-pane dependency, unbounded simulation, automatic retry, or monolithic builder.
- No automatic aesthetic rating/ranking, motion winner, biome winner, material winner, or silent
  hybridization.
- No plugin installation, external visual model, downstream transfer, HDA publish, or release tag
  under the base cycle authority.
- No claim that structural validation, a still, or a generated mockup constitutes creative motion
  evidence.

## Exit gate

Protected-main CI, clean pure/Ruff, Houdini 22.0.368 Hython regression, current-build probes,
repeatable manifests, readable source-built graph, bounded graph/data proof, hashed `.hipnc`, Gate V
and Gate I authentic pixels, at least one H2/R1 human-directed revision, preserved alternatives,
portable handoff, and truthful pending statuses for every unrun plugin/model/downstream gate.

No `v0.40.0` tag or release is implied by cycle completion.
