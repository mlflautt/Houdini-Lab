# Graph recipes

A **recipe** is a versioned, declarative description of a subgraph that Hermes can
instantiate with exposed variables. Recipes are the normal mid-level interface: more
stable and reusable than raw node creation, lighter than a full HDA.

## Format (YAML)

```yaml
id: sop.scatter_cluster_points
version: 1.0.0
summary: Scatter N points on a surface with attribute noise.
contexts: [SOP]
inputs:
  parent_path: {type: string}
  surface_path: {type: string}
  count: {type: integer, min: 1, max: 1000000, default: 1000}
  seed: {type: integer, default: 42}
references:
  surface: "{{surface_path}}"
nodes:                       # ordered create list
  - id: src
    type: "scatter::2.0"
    name: SCATTER_PTS
    role: seeded_points
    position: [0, 2]
    params: {forcetotal: "{{count}}"}
    comment: "Seed {{seed}}"
connections:
  - [surface, 0, src, 0]     # source id/output, destination id/input
outputs:
  - SCATTER_PTS
```

## Conventions
- `id` is `<context>.<snake_name>`; `version` is semver.
- Reference nodes by the local `id` in connections/outputs.
- Keep `contexts` explicit (SOP/OBJ/LOP/...).
- External node paths must be declared in `references`; dangling ids are rejected.
- Pin any SideFX Labs dependency in `meta.depends`.
- Bundled `.yaml` files are JSON-compatible YAML so bare `hython` can validate them with
  the standard library; general authored YAML uses the declared PyYAML dependency.
- `render_fragment` emits composable batch refs/operations/outputs; it supports a safe ref prefix
  and finite position offset for repeated subgraphs.
- `recipe.instantiate` is the normal execution path: one approval, checkpoint, transaction,
  rollback, diff, and replay log rather than separate partially applied create/connect calls.
- Bundled recipes are discovered one directory below `recipes/`, so SOP and LOP catalogs share
  the same version-aware registry while retaining explicit context categories.

See `docs/architecture.md` §5.3 / §10 for the tool/recipe/skill/HDA distinction.

`sop.differential_growth_loop@1.0.0` is the first recipe with an explicit editable feedback
boundary. The declarative outer graph creates and connects source, presentation, and output nodes;
the checkpointed `growth.solver.populate` tool fills only the pristine native Solver network with
the registered Relax → Attribute Blur → Resample composition. See
`docs/differential-growth.md`.

`cop.reaction_diffusion_pattern@1.0.0` is the first Copernicus recipe. It builds three explicit
Reaction Diffusion Begin/End pairs from one seeded activation mask, stores the native Gray–Scott
coefficients rather than relying on a UI preset callback, and exposes fixed-order human-selection,
mono-mask, contact-sheet, and managed image-export contracts. See
`docs/reaction-diffusion.md`.

`cop.procedural_material_foundry@1.0.0` consumes those mono patterns without hiding them and
derives four named native PBR channels for each of three material identities. The companion
`sop.material_swatch_gallery@1.0.0` supplies equal comparison geometry, while
`lop.procedural_material_foundry_stage@1.0.0` publishes native USD Material COP outputs through
Houdini 22's Texture Material Library, assigns every swatch simultaneously, and exposes one
bounded Karma stage. See `docs/material-foundry.md`.

`sop.lsystem_botanical@1.0.0` embeds three registered native L-System grammars rather than accepting
free-form rules. Canopy, fern, and coral retain named skeleton and PolyWire outputs, deterministic
seeds, a human Switch, and a side-by-side comparison with explicit framing. See
`docs/botanical-grammars.md`.

`sop.particle_calligraphy@1.0.0` builds three native temporal branches from one emitter. Readable
Add and Attribute Create/Delete stages normalize Houdini's legacy Particle output before Time
Blend and Particle Trail; named Time Shift contracts preserve the verified half-frame workaround.
Curve and PolyWire outputs feed a human Switch and fixed-order no-winner comparison. See
`docs/verification-ladder.md`.

`sop.vellum_membrane_lab@1.0.0` builds three independent native Cloth + Pin branches from one
seeded Grid contract. The reinforced branch adds Surface Struts, all solvers share an explicit
sphere-plus-floor collider, and each File Cache remains configured but unwritten. See
`docs/vellum-membrane-lab.md`.

`sop.mpm_matter_sculpture@1.0.0` builds three seeded native MPM Source branches, one explicitly
wired Container/Collider/Solver network, a non-writing File Cache, and selectable particle/surface
contracts. Material coefficients are stored directly rather than relying on the callback-driven
preset menu. See `docs/mpm-matter-sculpture.md`.

`sop.procedural_building_lot@1.0.0` preserves block, terrace, and needle massing branches behind
one editable Switch. `top.procedural_district@1.0.0` provides the native one-slot Wedge → ROP
Geometry → Wait for All orchestration contract. Together they keep lot computation, PDG
distribution, immutable caching, and downstream placement separately readable. See
`docs/procedural-district.md`.

`sop.rbd_art_directed_fracture@1.0.0` retains three native impact-point profiles behind a human
Switch, pins the current three-output Material Fracture definition, and separates rest pieces,
material constraints, proxy geometry, Bullet simulation, Simulation Point caching, Transform
Pieces reconstruction, and before/after presentation. See `docs/rbd-art-directed-fracture.md`.
