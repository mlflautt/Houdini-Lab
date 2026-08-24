# World Seed Atlas — Sprint 19

Sprint 19 composes Houdini Apprentice's native world-building systems into one editable, bounded,
and visually verified hero project. Three deterministic alien biomes remain simultaneous from SOP
construction through USD assembly and Karma proof. Mechanical validation can reject broken output,
but no code or manifest declares an aesthetic winner.

## Creative identities

| ID | Geological rhythm | Biome language | Atlas placement |
|---|---|---|---|
| `amber_mesa` | Broad high-amplitude terraced mesa | Small amber icosahedral outcrops and one landmark | -9.5 X |
| `verdant_rift` | Wider, lower green terraces | Dense dodecahedral growth and a central seed form | 0 X |
| `lunar_basin` | Fine low-amplitude blue-gray basin | Sparse tetrahedral shards and one hovering marker | +9.5 X |

The identities are seeds for human-directed development, not a ranking. Each carries an empty
`human_rating`, a stable ID and seed, explicit colors and geology controls, and `automatic_rank:
null`.

## Native graph

Each `sop.world_seed_biome@1.0.0` graph is:

```text
HeightField -> HeightField Noise -> HeightField Terrace -> Convert HeightField
                                      |                     |
                                      |                     +-> Color -> place -> OUT_TERRAIN
                                      +-> converted mesh -> Scatter -> OUT_BIOME_POINTS
                                                               |
Platonic -> Color --------------------------------------> Copy to Points -> place -> OUT_BIOME_FORMS
Platonic hero -> Color -----------------------------------------------------> place -> OUT_HERO
OUT_TERRAIN + OUT_BIOME_FORMS + OUT_HERO -> Merge -> OUT_WORLD
```

HOM creates, connects, tags, checkpoints, and inspects the graph. Native Houdini nodes generate
all terrain and geometry; there is no Python SOP or generated VEX. The three `OUT_WORLD` contracts
feed sequential SOP Import LOPs, one explicit camera and dome, bounded Karma Render Settings, and a
named USD stage output.

## Resource and license contract

- Houdini 22.0.368, `licenseCategoryType.Apprentice`.
- Native Houdini nodes and Karma CPU only; no plugin or third-party renderer.
- Terrain samples: 64, 96, or 128 per axis; 128 is the default and ceiling.
- Combined ceiling: 150,000 points and 150,000 primitives.
- One separately approved preview frame, default 768x432 and never above 1280x720.
- New `.hipnc`, JSON, SVG, and PNG artifacts only; no overwrite.

The Convert HeightField SOP produces adaptive meshes, so validation measures the cooked geometry
rather than assuming one output point per input voxel. The live default is substantially below its
ceiling.

## Verification

Pure tests cover deterministic planning, fixed candidate order, bounds, native recipe composition,
separate render approval, and no-winner metadata. Hython tests construct all three graphs, cook
geometry, verify exact roles/parameters/connections, validate `Cd`, compose the USD stage, capture
graph evidence, and save an incremented `.hipnc` fixture.

The final live acceptance produced:

- 2,442 total points and 2,292 total primitives;
- three valid USD world roots with geometry descendants;
- no node errors or warnings;
- a 768x432 Karma CPU image with all three panels present;
- a subject bounding box with 32-pixel left and 33-pixel right margins;
- no blank, exposure, crop, panel-presence, or duplicate flags;
- `winner: null` and `automatic_ranking: false` in every evidence layer.

The first camera proof cropped the side worlds. Two widened proofs improved the composition but
still touched the frame. The final atlas tightened only comparison placement from +/-11 to +/-9.5
units and passed without shrinking away biome detail. Those failed proofs remain in the local
acceptance lineage as troubleshooting evidence.

## Main artifacts

- Pure contracts and live validators: `hermes_houdini/world_seed.py`
- SOP recipe: `recipes/sop/world_seed_biome.yaml`
- LOP recipe: `recipes/lop/world_seed_atlas_stage.yaml`
- Skill: `skills/world.world_seed_atlas/`
- Acceptance harness: `scripts/run_sprint19_acceptance.py`
- Pinned node probe: `scripts/probe_world_seed_nodes.py`
- Final local proof root: `.hermes/sprint19-acceptance-20260823-k/`

## Next development

Sprint 20 adds plugin governance and a reversible SideFX Labs experiment. The native World Seed
Atlas remains the baseline. Any Labs-enhanced terrain, UV, baking, or presentation branch must
produce the same named output contracts and leave this plugin-free version fully usable.
