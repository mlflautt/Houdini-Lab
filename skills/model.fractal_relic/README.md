# model.fractal_relic

`model.fractal_relic@1.1.0` is the first complete creative skill in the repository. It builds three
deterministic alien-relic alternatives as readable native SOP branches, spatially arranges them
for comparison, and preserves them behind a human-controlled Switch. It does not generate VEX,
use a Python SOP, depend on selection/UI state, or choose a “best” result.

## Graph contract

Each candidate is:

```text
Sphere -> Attribute Noise 2.0 -> Scatter 2.0 -> Copy to Points 2.0
     \___________________________________________/ -> Merge -> OUT_CAND_*
```

The three `OUT_CAND_*` nodes feed two explicit continuations:

- translated presentation branches merge into `OUT_COMPARISON` for visual evaluation;
- unchanged branches feed `SELECT_CANDIDATE` and then `OUT_GEO` for a human choice.

Every created node has an exact name, declared SOP category/type, deterministic position,
`hermes_id`, role, creator, manifest version, batch ID, and candidate-lineage comment. The whole
graph is one approved `graph.apply_batch` transaction with a pre-edit `.hipnc` checkpoint,
rollback, diff, and append-only replay record.

## Artistic controls

- `seed` derives three recorded candidate seeds.
- `iterations` scales polygon/detail density.
- `detail_level` chooses a bounded draft/preview/final density tier.
- `base_radius`, `detail_radius`, and `noise_amplitude` shape the silhouette and surface language.
- `preview_candidate` sets the initial Switch input only; it is not a rating or winner.

The graph manifest records each candidate’s seed, parameter mutations, stable output ID, output
path, presentation offset, and empty `{score, notes, selected}` human-rating slot. No automatic
rank is produced.

## Execution and artifacts

The plan emits these ordered commands:

1. checkpointed `graph.apply_batch`;
2. explicit `OUT_COMPARISON` display-chain cook with point/primitive/memory/time estimates;
3. clean-cache geometry validation (finite bounds, warnings/errors, budget ceilings);
4. deterministic headless graph SVG;
5. graph/provenance JSON manifest with observed comparison metrics;
6. optional named viewer/viewport/camera capture at no more than 1280×720;
7. incremented final `.hipnc` snapshot that preserves the in-memory scene name.

All filesystem artifacts must be inside the caller’s approved absolute `artifact_dir`. Existing
observations are not overwritten unless the command policy explicitly allows it.

## Replay and verification

The Houdini integration test executes the complete headless plan, destroys the generated network,
replays the recorded batch into a clean same-named container, cooks again, and compares stable IDs,
point/primitive counts, and finite bounds. Interactive validation additionally captures and
visually inspects the three-form comparison through an explicit camera.

## Apprentice and HDA boundary

Generated scenes are Houdini Apprentice/non-commercial `.hipnc` artifacts. The inspectable graph
is composed from `sop.fractal_relic_candidate@2.0.0`, which is also the source for the promoted
`hermes::fractal_relic::2.0` `.hdanc`. The HDA adds controls and a single-output wrapper but retains
the same candidate/comparison geometry, proven by Houdini equivalence tests. Karma/Solaris preview
remains in the later lookdev stage rather than being smuggled into this SOP skill as hidden state.
