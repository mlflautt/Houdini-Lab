# Skills

A **skill** composes tools and recipes into a creative procedure with planning, validation,
observation, and refinement. A skill = a folder with `skill.yaml` (manifest) + `skill.py`
(module) + `README.md`.

## Manifest (`skill.yaml`)

Bundled manifests must remain JSON-compatible YAML. Houdini's stock Python does not include
PyYAML, so `skill_loader` uses `json.loads` as its standard-library fallback in bare Hython. Local
development may still use PyYAML for authoring checks; runtime correctness must not depend on it.

```yaml
id: model.fractal_relic
version: 1.1.0
summary: Build three comparable, seeded alien-relic forms from native SOP nodes.
contexts: [SOP]
houdini:
  minimum_version: "22.0"
  tested_builds: ["22.0.368"]
license:
  mode: houdini-apprentice-noncommercial
  commercial_use: false
intent_tags: [organic, growth, alien, procedural]
inputs:
  parent_node_id: {type: string}
  artifact_dir: {type: string}
  seed: {type: integer, default: 42}
  iterations: {type: integer, min: 1, max: 8, default: 4}
preconditions:
  - parent resolves to a SOP-capable geometry container
risk: medium
checkpoint: before_execute
cook_budget:
  max_points: 3000000
  max_seconds: 90
  max_frames: 1
steps:
  - recipe.compose: sop.fractal_relic_candidate@2.0.0
  - graph.apply_batch
  - geometry.validate
  - viewport.capture
verification:
  graph_checks: [all major branches end in named null nodes, no node errors]
  data_checks: [finite bounds, no NaN point positions, point count below budget]
  visual_checks: [readable primary silhouette, visible hierarchical branching]
outputs: [output_node_id, graph_manifest_path, preview_path]
rollback: restore_checkpoint
```

## Rules
- Purpose is narrow and documented.
- Contexts + exact Houdini builds declared.
- I/O + attribute contracts explicit.
- Risk + license explicit; checkpoints + rollback exist.
- Seeds reproducible; major stages named/null-contracted.
- Pure logic tested in `tests/unit`; HOM behavior in `tests/hython`.

See `docs/architecture.md` §5.3, §14, §21.

The first local-PDG skill is `generate.fractal_relic_variations@1.0.0`. It requires a published
relic HDA instance and composes bounded `pdg.variation.*` tools into immutable variation manifests,
one-slot local geometry jobs, an editable SOP gallery, and an optional explicit-camera contact
sheet. See `docs/pdg-variations.md`.

The first simulation skill is `simulate.vellum_relic_drop@1.0.0`. It composes
`sop.vellum_relic_drop@1.0.0`, an explicit bounded frame-range cook, static contract validation,
graph observation, an optional final-frame viewport capture, and a non-writing versioned File
Cache boundary. See `docs/vellum-simulation.md`.

The first Solaris/lookdev skill is `lookdev.relic_stage@1.2.0`. It composes a native LOP recipe,
three MaterialX builder candidates, explicit USD stage/material-binding validation, deterministic
graph observation, and an optional separately approved one-frame Karma CPU render. See
`docs/solaris-lookdev.md`.

The first native generative-feedback skill is `generate.differential_growth@1.0.0`. It composes
three source curves, one human selector, a registered Solver subgraph, an explicit 24-frame cook,
rest validation, outer/inner graph captures, and a provenance manifest without VEX, Python SOPs,
disk caches, or automatic ranking. See `docs/differential-growth.md`.

The first native Copernicus skill is `generate.reaction_diffusion_pattern@1.0.0`. It composes
three deterministic non-simulation Gray–Scott candidates, numeric and distinct-buffer validation,
a human selector, fixed-order contact sheet, graph/provenance capture, managed non-overwriting PNG
exports, and an incremented Apprentice scene snapshot. See `docs/reaction-diffusion.md`.

The first native grammar skill is `grow.botanical_grammar@1.0.0`. It composes three safe embedded
L-System candidates, exact rule and turtle-attribute validation, editable PolyWire branches, a
human selector, a fixed-order no-winner comparison, graph/provenance evidence, optional explicit
viewport capture, and an incremented Apprentice snapshot. See `docs/botanical-grammars.md`.

The first native particle-motion skill is `motion.particle_calligraphy@1.0.0`. It composes three
editable Particle Trail branches, optional project-relative baked envelope keyframes, a 48-frame
temporal validator, fixed-order human comparison, deterministic PNG mechanics, and an optional
hashed multimodal critique packet without performing inference or choosing a winner. See
`docs/verification-ladder.md`.

`simulate.vellum_membrane_lab@1.0.0` expands the simulation lane into three editable material
profiles with exact anchor/constraint checks, three independent temporal cooks, non-writing caches,
fixed-order human comparison, and optional deterministic/multimodal visual evidence. See
`docs/vellum-membrane-lab.md`.

`simulate.mpm_matter_sculpture@1.0.0` composes a proxy-first multi-material MPM graph, exact source
and solver validation, source mass plus per-frame temporal/resource metrics, an interruption-safe
progress manifest, a non-writing cache boundary, and optional deterministic/multimodal visual
evidence. See `docs/mpm-matter-sculpture.md`.

`world.procedural_district@1.0.0` composes registered native-SOP massing profiles with a one-slot
native TOP graph, immutable hashed lot caches, explicit district placement, an equal-scale labeled
gallery, structural/data validation, and optional visual evidence. The skill defaults to twelve
work items, requires explicit consent for local PDG child processes, and never ranks candidates.
See `docs/procedural-district.md`.

`simulate.rbd_art_directed_fracture@1.0.0` composes retained native impact profiles, pinned
three-output material fracture, proxy Bullet solving, compact Simulation Point cache boundaries,
Transform Pieces reconstruction, every-frame transform hashing, and optional before/after visual
evidence. Disk cache execution, Solaris staging, and final rendering remain separate operations.
See `docs/rbd-art-directed-fracture.md`.

`lookdev.procedural_material_foundry@1.0.0` composes reusable Gray-Scott patterns into twelve
named Copernicus PBR channels, three native USD Material COP contracts, equal SOP swatches, and a
Texture Material Library Solaris stage. It verifies component/range/hash/color-space intent and
all three MaterialX bindings before an optional one-frame Karma gallery; candidate ratings remain
empty and no winner is inferred. See `docs/material-foundry.md`.
