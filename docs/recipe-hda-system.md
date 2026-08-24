# Recipe and HDA promotion system

Sprint 5 promotes verified graphs without changing the repository’s graph-first hierarchy:

```text
versioned recipe data -> composable graph-batch fragment -> checkpointed skill graph
                      \-> shared graph specification -> parameterized HDA source builder
```

The recipe, raw skill, and HDA therefore share topology instead of copying a tutorial or hiding
the graph inside generated Python.

## Versioned catalog

The central registry indexes tools, recipes, and HDA builders by name and numeric dotted version.
`registry.describe` lists the catalog, and `recipe.describe` returns a recipe’s contexts, inputs,
outputs, cook budget, and source. Numeric comparison means `1.10.0` correctly supersedes `1.2.0`.

Bundled catalog entries include:

- `sop.fractal_relic_candidate@2.0.0`;
- `sop.scatter_cluster_points@1.0.0`;
- `sop.sweep_petals@1.0.0`;
- `hermes::fractal_relic@2.0.0` (builds operator type `hermes::fractal_relic::2.0`).

## Transactional recipe fragments

`Recipe.render_fragment` resolves typed inputs into JSON-only `graph.apply_batch` operations. A
fragment contains its recipe id/version, local refs, declared outputs, exact names, native operator
types, parameters, comments, positions, connections, and flags. `ref_prefix` and a finite 2D
position offset let a skill combine several copies without collisions.

`recipe.instantiate` is medium-risk. It renders one registered fragment, saves a pre-edit `.hipnc`
checkpoint, executes one allowlisted graph transaction, rolls back on failure, returns the graph
diff and recipe outputs, and appends the exact replay JSONL. The dispatcher requires a single-use
approval for the exact stored envelope.

## Fractal relic promotion

`model.fractal_relic@1.1.0` and `hermes::fractal_relic::2.0` both call the pure
`skills._lib.fractal_relic.build_graph_spec` function. That function composes three instances of
`sop.fractal_relic_candidate@2.0.0` plus the comparison Merge and human-selection Switch.

The HDA builder uses HOM only to instantiate and package those native operations. Each internal
recipe node retains a deterministic stable id, semantic role, recipe ref/version, builder id, and
lineage comment. The asset adds only two wrapper nodes for selecting either `OUT_GEO` or
`OUT_COMPARISON` as its single SOP output.

Promoted controls:

- form: base radius, detail radius, noise amplitude;
- variation: seed, iterations, bounded detail tier;
- selection: preview candidate and selected/comparison output mode;
- human decision: winner, three 0–5 rating slots, and three note fields;
- provenance: recipe id/version and Apprentice license mode.

`Preview Candidate` drives geometry but is not a winner. `Human Winner` and rating fields record
creative judgment and do not automatically rank or mutate candidates.

The definition embeds `Help` and `hermes_manifest.json` sections with source skill/recipe, license,
engine restriction, cook budget, and human-selection policy.

## Publishing and upgrades

`hda.build_registered` is medium-risk and writes only inside an approved `dest_dir`. It creates a
new `.hdanc` and refuses an existing destination; there is no overwrite argument in the registered
safe-mode tool. Publishing remains non-commercial and does not enable Houdini Engine.

`upgrade_from_v1` creates no replacement and deletes nothing. Given an existing v1-like source and
a new `hermes::fractal_relic::2.0` target, it copies only the compatible `seed`, `iterations`, and
`detail_level` controls and tags the target with its source type. The artist keeps the original
network until they explicitly accept and remove it.

## Verification

Pure tests validate catalog resolution, typed substitution, fragment composition, safe refs and
positions, and approval gates. Houdini tests verify operator/parameter availability, exact recipe
instantiation, HDA controls and expressions, stable metadata, help/manifest sections, no generated
Python/VEX nodes, non-overwriting `.hdanc` publication, v1 migration, and geometry equivalence
between the raw graph and HDA comparison output.

Binary `.hdanc` and `.hipnc` outputs remain generated artifacts. The committed source of truth is
the recipe YAML, shared graph specification, HDA build script/manifest, and tests.
