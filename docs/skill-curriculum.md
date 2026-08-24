# Creative skill curriculum

Ten stages from graph literacy to a cross-tool creative pipeline. Full text in
`docs/architecture.md` §14; this lists the stages and the first creative skills to build.

1. **Graph literacy & scene inspection** — three-forms scene via typed tools.
2. **Procedural modeling** — relic generator, modular architecture, alien botanical, terrain, abstract sculpture, ornamental, CNC-ready.
3. **Attributes & VEX** — growth fields, attraction/repulsion, layered noise, generative color, point-cloud choreography.
4. **Motion & audio-reactive** — beat-driven pulses, spectrum fields, visualizers for generated music, MIDI/OSC-controlled HDAs (your music workflow).
5. **Materials, Copernicus, lookdev** — alien surfaces, weathering, procedural glyphs, texture/mask outputs for ComfyUI.
6. **Simulation** — Vellum membranes, RBD fracture, sparse Pyro, FLIP liquid sculpture.
7. **Solaris & USD** — assemble worlds, variant sets, reusable USD components, light/camera rigs.
8. **PDG & variation** — 100 form variants, contact sheets, HDA seed validation, training datasets.
9. **HDA authoring** — namespaces/versions, help, examples, backward compat, source expansion.
10. **Cross-tool pipeline** — Houdini → Blender → ComfyUI → DaVinci Resolve, archived with provenance.

## First implementation roadmap (sprints)
0. Install + capability manifest · 1. Bridge + read-only inspection · 2. Foundational graph editing
· 3. Cook/observation/validation · 4. First skill (`model.fractal_relic` / `world.biobloom_cluster` /
`motion.audio_reactive_field`) · 5. Recipe + HDA system · 6. Local PDG variations · 7. Simulation recipe
· 8. Solaris + lookdev.

Implementation status: sprints 0–14 are present in package version 0.15.0. Sprint 5 promotes the
verified relic topology into `sop.fractal_relic_candidate@2.0.0` and the parameterized
`hermes::fractal_relic::2.0` HDA, backed by a version-aware catalog, transactional recipe tool,
non-overwriting HDA publisher, embedded provenance/help, human rating controls, v1 migration, and
raw-graph/HDA equivalence tests. Sprint 6 adds a bounded one-slot native Wedge/ROP Geometry lane,
immutable work-item/result manifests, explicit external-process consent, validated `.bgeo.sc`
caches, and an editable contact-sheet gallery without automatic ranking. Sprint 7 adds
`sop.vellum_relic_drop@1.0.0`, `simulate.vellum_relic_drop@1.0.0`, a native Cloth + Pressure
Vellum graph, configured non-writing File Cache boundary, and an explicit policy-bounded
frame-range cook with per-frame metrics and timeline restoration. Sprint 8 adds
`lop.relic_lookdev_stage@1.0.0`, `lookdev.relic_stage@1.0.0`, three native MaterialX candidates,
bounded USD composition/material-binding validation, and a separately approved one-frame Karma
CPU preview through a managed USD Render ROP. Sprint 9 adds
`sop.differential_growth_loop@1.0.0`, `generate.differential_growth@1.0.0`, three editable native
source curves behind a human Switch, and a checkpointed Solver feedback graph composed only of
Relax, Attribute Blur, and Resample SOPs. Its 24-frame in-memory cook records per-frame topology,
captures both graph levels, and leaves final Karma proof as a separately attributable reuse of
Sprint 8 lookdev. Sprint 10 adds `cop.reaction_diffusion_pattern@1.0.0` and
`generate.reaction_diffusion_pattern@1.0.0`: one Float32 CopNet, three native Gray–Scott block
pairs, fixed-order mono and color contracts, a human Switch, a native Contact Sheet, and managed
PNG exports. Its validation checks callback-derived coefficients and distinct image hashes as well
as finite range, variance, resolution, messages, memory, and elapsed time. Sprint 11 adds
`sop.lsystem_botanical@1.0.0` and `grow.botanical_grammar@1.0.0`: three safe registered native
L-System skeletons, editable PolyWire branches, a human Switch, and an explicitly framed
comparison. Exact premise/rule, turtle-attribute, topology, ordering, memory, and time validation
keeps arbitrary grammar text and rule-file IO outside safe mode. Sprint 12 adds
`sop.particle_calligraphy@1.0.0` and `motion.particle_calligraphy@1.0.0`: three native Particle →
Time Blend → Particle Trail → PolyWire branches, explicit legacy `life` normalization, a verified
half-frame compatibility boundary, optional project-relative baked-envelope keyframes, and
48-frame validation. Native candidate/seed labels are retained in a separate editable output so
label geometry cannot disturb render framing. It also introduces the repository-wide
[verification ladder](verification-ladder.md): deterministic image mechanics first, then an
optional hashed packet for local or explicitly approved external multimodal critique, with no
automatic aesthetic winner. Sprint 13 adds three independently solved native Vellum membrane
profiles with exact anchor, constraint, cache, temporal, and visual checks. Sprint 14 adds a single
multi-material native MPM sculpture with explicit granular-like, elastic-like, and viscous-like
coefficients, a 24-frame/150k-particle safe proxy boundary, optional native surfacing, and a durable
per-frame cache-progress manifest while leaving geometry cache writes disabled.

## First acceptance test
From a clean Apprentice scene, Hermes must: report build/Python/license/renderer; set+validate
`$JOB`; inspect+summarize graph; checkpoint `.hipnc`; build a readable three-forms SOP network
with stable IDs; expose ≥3 controls + 1 seed; cook display chain within budget; return diff/metrics/
cook time; capture viewport + graph image; Karma CPU preview (Apprentice-compliant); verify no
source overwrite + non-commercial; save versioned `.hipnc`; replay command log into a clean scene
with equivalent results.

Sprints 4–11 close the modeling, cook, validation, viewport, graph, snapshot, replay, generative
feedback, and Karma CPU preview portions of this acceptance test. Sprint 8 keeps USD stage
composition and external rendering separately attributable and leaves all three material
candidates available for human judgment. Sprint 9 proves that the same lane can present a
stateful native-SOP growth result without merging its solver and render approvals. Sprint 10 adds
native 2D procedural-mask generation and proves the candidate images themselves, not just preset
menu tokens, before export. Sprint 11 establishes a dependency-free native grammar lane whose
three editable source variants remain available for human judgment.

## Generative development roadmap (sprints 9–19)

This second roadmap turns a set of representative Houdini workflows into small, composable
Hermes capabilities. It is deliberately ordered from inexpensive SOP feedback to heavier DOP,
TOP, and cross-context systems. Every stage preserves the editable graph, deterministic seed,
lineage, and unfilled human-rating fields; a gallery is a comparison surface, not an automatic
ranking.

| Sprint | Creative system | Planned recipe and skill | Context contract | Default resource boundary | Acceptance evidence |
|---|---|---|---|---|---|
| 9 | Native differential growth | `sop.differential_growth_loop@1.0.0`; `generate.differential_growth@1.0.0` | SOP source candidates → native Solver feedback → curve and PolyWire contracts | 24 frames, ≤50k points, one selected source, no external process | Rest/final geometry metrics, graph SVG, checkpoint, one Apprentice-safe Karma preview |
| 10 | Reaction-diffusion masks | `cop.reaction_diffusion_pattern@1.0.0`; `generate.reaction_diffusion_pattern@1.0.0` | Copernicus reaction-diffusion block → named image/mask outputs | 256² default, 512² ceiling, ≤48 integration steps | Channel/range/hash metrics, deterministic image artifacts, contact sheet, provenance |
| 11 | Botanical grammars | `sop.lsystem_botanical@1.0.0`; `grow.botanical_grammar@1.0.0` | Built-in L-System skeleton → width-aware PolyWire → selected/comparison contracts | ≤6 generations, ≤250k points/primitives, safe registered grammars only | Grammar/seed manifest, topology/attribute metrics, three editable source variants, bounded Karma proof |
| 12 | Particle calligraphy | `sop.particle_calligraphy@1.0.0`; `motion.particle_calligraphy@1.0.0` | SOP particles → Particle Trail → ribbon/tube outputs; optional baked audio envelope input | 48 frames, ≤100k trail points, audio is project-relative data | Per-frame trail metrics, rest/final comparison, silent deterministic fixture |
| 13 | Vellum membranes and hybrid matter | `sop.vellum_membrane_lab@1.0.0`; `simulate.vellum_membrane_lab@1.0.0` | Native Vellum constraints/solver with visible source, collider, cache, and output contracts | 48 frames, ≤75k points, cache writes separately approved | Constraint counts, frame metrics, cache manifest, preview, editable alternatives |
| 14 | MPM matter sculpture | `sop.mpm_matter_sculpture@1.0.0`; `simulate.mpm_matter_sculpture@1.0.0` | MPM Source/Collider/Container/Solver → configured cache boundary → surface or points | Proxy first; 24 frames; ≤150k safe default; ≤1M and geometry cache/render separately approved | Explicit profile manifest, source mass and per-frame bounds metrics, proxy preview, interruption-safe progress |
| 15 | Terrain ecosystems | `sop.heightfield_ecosystem@1.0.0`; `world.heightfield_ecosystem@1.0.0` | HeightField massing/seeding/remap/erosion → named masks → scatter-ready outputs | 512² default, 1024² ceiling, bounded erosion passes | Height/mask statistics, erosion comparison, tile manifest, terrain preview |
| 16 | PDG city and world generation | `top.procedural_district@1.0.0`; `world.procedural_district@1.0.0` | TOP wedge/work items orchestrate SOP lot/building recipe; immutable result manifests | One local slot, 12 lots default, no background process without consent | Work-item graph, validated caches, district assembly, no-winner gallery |
| 17 | Art-directed RBD | `sop.rbd_art_directed_fracture@1.0.0`; `simulate.rbd_art_directed_fracture@1.0.0` | Material fracture/constraints → Bullet proxy → cached transforms → optional Solaris procedural | 48 frames, proxy geometry, ≤5k pieces; full sim/render separately approved | Piece/constraint metrics, transform cache validation, before/after preview |
| 18 | Copernicus material foundry | `cop.procedural_material_foundry@1.0.0`; `lookdev.procedural_material_foundry@1.0.0` | COP pattern layers → named PBR channels → MaterialX candidates → USD binding | 512² default, 1024² ceiling, three candidates, one approved preview | Channel validation, swatch sheet, USD binding checks, one Karma preview |
| 19 | World Seed Atlas | `sop.world_seed_biome@1.0.0`; `world.world_seed_atlas@1.0.0` | Three native HeightField biomes → named terrain/scatter/hero contracts → simultaneous USD stage | 128² terrain per seed, ≤150k combined points/primitives, one approved preview | Exact seed/graph validation, three USD roots, object/LOP evidence, crop-safe Karma atlas |

### Stage contracts and source notes

**Sprint 9 — differential growth.** The first implementation uses the native two-force idea from
SideFX's [Complex Growth in 2 Nodes](https://www.sidefx.com/tutorials/complex-growth-in-2-nodes/):
point separation pushes a curve outward while [Attribute Blur](https://www.sidefx.com/docs/houdini/nodes/sop/attribblur.html)
relaxes `P`; [Resample](https://www.sidefx.com/docs/houdini/nodes/sop/resample.html) maintains usable
edge spacing and [PolyWire](https://www.sidefx.com/docs/houdini/nodes/sop/polywire.html) provides a
renderable branch. Hermes will populate only this registered native subgraph inside a Solver,
expose force/spacing/frame controls, and retain three seeded source curves behind a human-selected
Switch. It will not implement the point iteration in Python or hide it in a Python SOP.

**Sprint 10 — reaction diffusion.** Use Houdini 21+'s native Copernicus
[Reaction Diffusion Block Begin](https://www.sidefx.com/docs/houdini/nodes/cop/reactiondiffusion_block_begin.html)
and [Block End](https://www.sidefx.com/docs/houdini/nodes/cop/reactiondiffusion_block_end.html) as the
safe baseline. SideFX-hosted examples on [weighted SOP reaction diffusion](https://www.sidefx.com/tutorials/houdini-algorithmic-live-weighted-reaction-diffusion/),
[3D volume reaction diffusion](https://www.sidefx.com/tutorials/reaction-diffusion-part-ii-implementation/),
and [artistic uses](https://www.sidefx.com/learn/talks/fun-with-reaction-diffusion-in-houdini/)
remain study references, not code to paste wholesale. The initial capability emits masks and
textures; later stages may consume them for displacement, scattering, and MaterialX.

Implemented in package 0.11.0. The safe baseline uses deterministic non-simulation mode, caps
`Iterations × Iterations per Step` at 48, and keeps each native Begin/End pair at one CopNet level.
The 256² default emits a 768×256 comparison. Acceptance exposed a Houdini parameter-callback trap:
setting `presetsgs` recorded three tokens but left identical default coefficients and mono buffers.
The final recipe explicitly stores the native Small Waves, Large Waves, and Spots coefficient
sets. `cop.reaction.validate` refuses stale coefficients, duplicate SHA-256 image buffers,
non-finite pixels, weak range/variance, messages, resolution drift, or policy overages. Selection
remains a human Switch input and no winner is written. See
[`docs/reaction-diffusion.md`](reaction-diffusion.md) for the verified evidence.

**Sprint 11 — branching grammars.** The dependency-free baseline is Houdini's built-in
[L-System SOP](https://www.sidefx.com/docs/houdini/nodes/sop/lsystem) and SideFX's
[L-System node lesson](https://www.sidefx.com/tutorials/l-systems-node/?collection=63). The
[Labs Curve Branches SOP](https://www.sidefx.com/docs/houdini/nodes/sop/labs--curve_branches.html)
is an optional extension only after a separately approved, pinned SideFX Labs installation. Safe
mode accepts versioned grammar templates; free-form generated grammar text remains development
mode and must pass size and generation limits.

Implemented in package 0.12.0. Safe mode embeds exact canopy, fern, and coral premises and
productions, records deterministic per-candidate seeds, enables documented L-System point
attributes, and disables rule-file IO. A native width-aware PolyWire follows every skeleton. The
public ceiling is six generations rather than the roadmap's original eight: the radial coral's
five-way production grows fast enough that six is a more responsible reusable contract. The
verified six-generation default produced 47,248 comparison points and 91,817 primitives, observed
about 21.1 MB of geometry, and validated in 0.311 seconds. Visual acceptance used generation five
and a separately attributable 768×432 Karma CPU proof. Early proofs with default turtle width and
unframed comparison placement were retained; their sparse/clipped results led to explicit width and
framing parameters that `botanical.validate` now checks. See
[`docs/botanical-grammars.md`](botanical-grammars.md).

**Sprint 12 — particle calligraphy.** Houdini's native
[Particle Trail SOP](https://www.sidefx.com/docs/houdini/nodes/sop/particletrail.html) is the graph
center. Attribute-driven width, color, and age become downstream ribbon/tube controls. Music input
is a deterministic, project-relative envelope artifact; live MIDI/OSC is a later explicit external
session, never a hidden prerequisite for the fixture.

Implemented in package 0.13.0. The safe fixture creates arc, fan, and orbit branches from a shared
twelve-point emitter. Live Houdini 22.0.368 probing exposed two legacy Particle SOP boundaries: its
source primitive must be removed while retaining simulated points, and its vector2 `life` tuple
must be normalized to scalar `age` and `life`. Particle Trail also produced valid samples at
intervening half-frames while exact integer cooks were empty; the recipe therefore exposes a named
Time Shift using `$FF - 0.5` with integer rounding disabled, and the validator asserts the
workaround. Optional audio response accepts only bounded `hermes.audio_envelope.v1` JSON relative
to an explicit project root and refuses existing wind keyframes. Final live acceptance covered all
48 frames in 2.47 seconds, peaked at 2,538 trail points, and produced 846 trail points plus 4,230
tube points per candidate. The verification loop caught an initially crushed/sparse render, then a
near-edge composition; the final 768×432 Karma CPU evidence passes the tightened two-percent crop,
panel-presence, exposure, occupancy, contrast, and edge checks. Candidate labels remain a separate
native output after direct label merging was shown to disturb the render contract. See the
[verification ladder](verification-ladder.md) for deterministic pixel checks and the
local/external multimodal critique plan.

**Sprint 13 — Vellum.** Expand the Sprint 7 temporal/caching controller using the official
[Vellum overview](https://www.sidefx.com/products/houdini/vfx/vellum/),
[Vellum documentation](https://www.sidefx.com/docs/houdini/vellum/index.html), and
[Vellum introductory lesson](https://www.sidefx.com/tutorials/vellum-i/). Fluid-like presets may
follow the [Vellum fluids starter pack](https://www.sidefx.com/tutorials/h19-vellum-fluids-starter-pack/),
but every result must still expose native constraints, solver, cache, and material-independent
geometry for continued artist editing.

Implemented in package 0.14.0. One explicit 25×25 Grid and anchor group feed silk, rubber, and
reinforced Cloth + Pin branches, each with an independent Vellum Solver and non-writing File Cache.
The reinforced branch adds verified Surface Struts: live Houdini 22.0.368 probing showed ordinary
Struts add nothing to the open sheet, while Surface Struts increased the default constraint graph
from 3,456 to 6,838 primitives. The same probe caught a dangerous Pin parameter ambiguity that
froze every point; validation now proves exactly 25 zero-mass anchors and 600 dynamic points. Every
frame records topology, bounds, centroid, memory, messages, and cook time, then verifies anchor
drift, deformation, candidate distinctness, selection, cache non-writing, and restored timeline.
Final 24-frame acceptance validated in 16.22 seconds with zero anchor drift and 1.35–1.39 units of
mean dynamic displacement; its 768×432 three-silhouette Karma comparison passed the deterministic
visual gate without flags.
See [`docs/vellum-membrane-lab.md`](vellum-membrane-lab.md).

**Sprint 14 — MPM.** Follow SideFX's four-part
[MPM workflow](https://www.sidefx.com/docs/houdini/mpm/workflow.html): Source, Collider, Container,
and Solver. Snow, soil, mud, concrete, metal, jello, rubber, water, honey, and sand presets are
candidate starting points, not claims of physical identity. Proxy validation is mandatory before
any larger particle/cache budget is requested.

Implemented in package 0.15.0. Three seeded native source volumes feed one fixed-order
multi-material Solver through explicit Container wires. The recipe records granular-like,
elastic-like, and viscous-like coefficients directly because the installed Material Preset menu is
callback-driven; parameter round-trip validation also caught and removed an out-of-range viscosity
value. One static VDB collider and the Solver ground plane create the interaction sculpture. A
non-writing File Cache precedes both a particle contract and optional native MPM Surface, selected
by an editable Switch without ranking materials. Source outputs prove density and estimated mass;
every Solver frame proves topology, finite bounds, source identities, motion, memory, substeps, and
cook time. A durable progress JSON updates after every completed frame and remains failed or
complete after interruption. See [`docs/mpm-matter-sculpture.md`](mpm-matter-sculpture.md).

**Sprint 15 — terrains.** Encode the staged SideFX
[terrain-creation workflow](https://www.sidefx.com/docs/houdini/heightfields/creation.html) as
readable branches: massing, seed/noise, remap, upsample, shaping, re-seeding, erosion, and final
adjustment. Multi-scale passes follow the guidance in
[terrain erosion](https://www.sidefx.com/docs/houdini/heightfields/erosion.html) and the
[HeightField Erode SOP](https://www.sidefx.com/docs/houdini/nodes/sop/heightfield_erode). Houdini
22's [world-building updates](https://www.sidefx.com/products/whats-new-in-h22/world-building/)
inform future biome and scatter integration without becoming a moving unpinned dependency.

**Sprint 16 — procedural districts.** The SideFX
[Build a City with PDG](https://www.sidefx.com/tutorials/foundations-build-a-city-with-pdg/)
lesson supplies the compositional model. The implementation reuses Sprint 6's one-slot scheduler,
write sentinels, work-item manifests, and editable no-winner gallery; TOPs distribute declared
recipe parameters rather than opaque arbitrary scripts.

Implemented in package 0.16.0 as a self-contained capability because Sprint 15 terrain is still
deferred in this checkout. Three readable native-SOP profiles feed a fourteen-attribute Wedge,
foreground ROP Geometry output, one-slot Local Scheduler, Wait for All barrier, immutable SHA-256
cache records, deterministic lot placements, a spatial district, and a fixed-order labeled
no-winner gallery. The default is twelve lots on a four-by-three grid; 4–16 are accepted under
5,000-point/primitive per-item ceilings. Terrain-adaptive placement remains a future composition,
not a hidden dependency. Live Houdini 22.0.368 acceptance completed all twelve caches in 56.831
seconds, assembled 2,696 points / 2,598 primitives, and closed on a 768×432 Karma proof whose
camera refinements are retained and whose final deterministic report passes without flags. See
[`docs/procedural-district.md`](procedural-district.md).

**Sprint 17 — RBD.** Begin with native material fracturing and constraints as demonstrated in
[Introduction to Material-Based Destruction](https://www.sidefx.com/docs/houdini/destruction/tutorials/intro_to_mbd_1.html)
and the [Violin RBD Shatter](https://www.sidefx.com/tutorials/violin-rbd-shatter/) example. Houdini
22's [RBD updates](https://www.sidefx.com/docs/houdini/news/22/rbd.html) and the Solaris
[Houdini RBD Procedural](https://www.sidefx.com/docs/houdini/solaris/houdini_rbd_procedural.html)
define the later transform-to-USD path. Fracture, simulation, cache, and stage/render remain
separately attributable operations.

Implemented in package 0.17.0 as `sop.rbd_art_directed_fracture@1.0.0` and
`simulate.rbd_art_directed_fracture@1.0.0`. Three deterministic native impact fields remain behind
a human Switch; pinned Material Fracture 4.0 emits named rest pieces, material Glue constraints,
and proxies into one bounded Bullet solve. The Solver's compact Simulation Points output provides
the explicit `name/P/orient/pivot/scale/v/w` transform-cache contract and reconstructs the editable
rest polygons through Transform Pieces. The safe default is 48 frames and at most 5,000 pieces;
disk cache writes, Solaris procedural staging, and full rendering remain separate approval
boundaries. Initial live H22.0.368 acceptance produced 25 pieces, broke all 89 constraints, dropped
3.819992 units, retained deterministic per-frame transform hashes, restored the timeline, and
wrote no cache files. Two flagged camera attempts were retained; the final 768×432 Karma proof
passes deterministic two-panel crop/presence analysis with no flags and no automatic winner. See
[`docs/rbd-art-directed-fracture.md`](rbd-art-directed-fracture.md).

**Sprint 18 — material foundry.** Combine reusable Copernicus pattern recipes, including the
techniques in SideFX's [organic textures lesson](https://www.sidefx.com/tutorials/how-to-create-organic-textures/?collection=539),
with the documented [COP material workflow](https://www.sidefx.com/docs/houdini/copernicus/working_with_cops.html).
The [Houdini 22 Copernicus examples](https://www.sidefx.com/docs/houdini/news/22/copernicus.html) and
[heightfield texture scene](https://www.sidefx.com/contentlibrary/heightfield-textures/) are visual
references. The stage is complete only when named PBR channels, color-space intent, MaterialX
bindings, swatches, and a bounded Karma proof all agree.

Implemented in package 0.18.0 as `cop.procedural_material_foundry@1.0.0`,
`sop.material_swatch_gallery@1.0.0`, `lop.procedural_material_foundry_stage@1.0.0`, and
`lookdev.procedural_material_foundry@1.0.0`. Three fixed-order Gray-Scott patterns feed explicit
native base-color ramps, scalar roughness/height remaps, offset height-to-normal conversions, and
USD Material COPs. `base_color` declares scene-linear Rec.709 intent; roughness, height, and normal
remain raw data. Houdini 22's Texture Material Library publishes all three materials and one
Assign Material LOP binds equal swatches simultaneously, so validation cannot collapse into a
single selected look. Live H22.0.368 acceptance at 256² verified all twelve finite, varied channel
buffers, their component counts and 0–1 data ranges, every connected MaterialX output, and all
three computed USD bindings. The first Karma camera proof was retained after deterministic QA
flagged cropping; the widened 768×432 proof passes three-panel presence/crop analysis with no flags
and still writes no aesthetic winner. See [`docs/material-foundry.md`](material-foundry.md).

### Cross-stage rules

- Native nodes and readable composition are the source of truth; HOM may construct or inspect a
  registered graph but must not replace its computation.
- Each capability declares Houdini build/context/node types, seed, frame or iteration range,
  point/voxel/pixel ceiling, risk class, checkpoint, rollback, and project-relative artifacts.
- Expensive simulation, cache writes, background PDG work, plugin installs, and final rendering
  remain separate approval boundaries. Apprentice output stays at or below 1280×720.
- Every creative comparison retains stable candidate IDs, lineage, empty human-rating fields, and
  all alternatives. Validation may reject a broken candidate but never silently choose a winner.
- Each sprint closes pure-Python tests, Hython integration tests, replayable fixture construction,
  structural and numeric validation, graph capture, visual evidence, Ruff, and package smoke tests.
- Visual verification follows the [verification ladder](verification-ladder.md): structural/data
  evidence, deterministic pixel mechanics, optional local VLM, optional explicit external critic,
  then human judgment only for unresolved taste or disagreement.

### Optional renderer and plugin lane

Third-party tools remain a gated experimental lane rather than Sprint 19's hidden foundation.
The first audit found the downloaded Octane 2025.2.1 Prime bundle compiled only for Houdini
19.5–20.5, while this workstation runs Houdini 22.0.368 Apprentice. SideFX explicitly disallows
third-party renderers under Apprentice, and OTOY's exact H22 build is now Octane 2026.4.0.0.
Accordingly no plugin was installed. The future sequence is license upgrade → exact archive/hash
audit → versioned external extraction → disabled/reversible package JSON → isolated startup probe
→ low-resolution fixture → optional renderer recipes. SideFX Labs, Substance via Labs, and MOPs
form the higher-priority construction-tool track. See
[`renderer-plugin-expansion-plan.md`](renderer-plugin-expansion-plan.md).

### Apprentice creative expansion

**Sprint 19 — World Seed Atlas.** Treat the current Apprentice installation as the primary
creative platform rather than waiting for a renderer or license upgrade. Compose Houdini 22's
native Copernicus terrain tools, procedural materials, botanical grammar, district scattering,
Solaris assembly, PDG variants, and bounded simulation accents into three deterministic alien
biomes. The atlas becomes the plugin-independent baseline: every later enhancement must remain an
optional branch with the same named contracts and a functioning native fallback.

Implemented in package 0.19.0 as `sop.world_seed_biome@1.0.0`,
`lop.world_seed_atlas_stage@1.0.0`, and `world.world_seed_atlas@1.0.0`. Three fixed identities—
Amber Mesa, Verdant Rift, and Lunar Basin—use exact seeded native HeightField Noise and Terrace
graphs, adaptive mesh conversion, bounded Scatter/Copy to Points biomes, and independent hero
contracts. All three feed one simultaneous USD/Karma stage. Live H22.0.368 Apprentice acceptance
produced 2,442 points and 2,292 primitives, valid USD descendants, clean node messages, and a
768x432 proof whose three panels pass presence and crop analysis with no flags. Candidate ratings
remain empty and no winner is authored. See [`world-seed-atlas.md`](world-seed-atlas.md).

**Sprint 20 — SideFX Labs integration.** Implemented in package `0.20.0`. The pure registry audits
plugin class, exact build, checksum, package JSON, tree contents, permissions, fixtures, and
rollback without importing Houdini. The approved SideFX Labs `22.0.368` production archive is
installed in user scope. Enabled startup exposes 450 matching types; three exact SOP types—Measure
Curvature 3.1, Terrain Analysis 1.0, and Instance Attributes 1.0—pass bounded editable fixture
graphs, saved `.hipnc` evidence, and a crop-safe 768x432 Karma proof. The verified filename-qualified
skip list restores the three-node baseline. MOPs was deliberately deferred to the separately gated
Sprint 22 experiment. See
[`sidefx-labs-integration.md`](sidefx-labs-integration.md).

**Sprint 21 — Labs-enhanced World Seed Atlas.** Implemented in package `0.22.0` as
`sop.world_seed_labs_enhancement@1.0.0`, `sop.world_seed_labs_unavailable@1.0.0`, and
`world.world_seed_atlas_labs@1.0.0`. The native Sprint 19 graph is composed first; capability-gated
overlays then use only the three exact Sprint 20 Labs types. Native remains Switch input zero.
Enabled acceptance produced 4,734 points/4,440 primitives and a six-panel visual pass. A separate
package-skipped bare-Hython run instantiated no plugin nodes and cooked all native worlds. See
[`labs-enhanced-world-seed-atlas.md`](labs-enhanced-world-seed-atlas.md).

**Sprint 22 — MOPs kinetic reliquary.** Implemented in package `0.22.0` as
`sop.kinetic_reliquary_native@1.0.0`, capability-gated MOPs/unavailable overlays,
`lop.kinetic_reliquary_stage@1.0.0`, and `motion.kinetic_reliquary@1.0.0`. MOPs v1.12 is pinned and
isolated from global preferences. Native, plain, animated-noise, and moving-shape branches retain
24 packed pieces with equivalent `P/orient/scale/v/seed/variant_id` contracts across frames
1/12/24. Three crop-safe, nonduplicate four-panel Karma proofs pass mechanical QA; a zero-MOPs
launch retains the native graph. See [`mops-kinetic-reliquary.md`](mops-kinetic-reliquary.md).

**Sprint 23 — staged reliquary and perceptual verification.** Implemented in package `0.23.0` as
`motion.kinetic_reliquary@1.1.0` plus new staged SOP/LOP recipes. Presentation begins after the
verified packed contracts: camera-facing outer orbits, counter-rotating inner orbits, and focal
cores create four readable mechanisms. The visual gate now records grid cells, normalized centers,
margin balance, consecutive-frame pixel change, and motion coverage. The final proof passes with
40% vertical motion coverage; no metric ranks candidates. See
[`sprint23-aesthetic-verification.md`](sprint23-aesthetic-verification.md).

**Sprint 24 — bounded local visual critic.** Implemented in package `0.24.0` as three registered
verification tools: loopback probe, explicitly enabled advisory inference, and deterministic
calibration scoring. Exact packet hashes and structured response provenance are retained; model
installation/startup is never implicit, and aesthetic selection remains human-owned. Live Qwen3-VL
calibration is pending. See [`local-vision-critic.md`](local-vision-critic.md).

**Sprint 25 — verification routing and human gates.** Implemented in package `0.25.0` as
`verification.route@1.0.0`. The pure router hashes every report, preserves the mechanical gate,
requires exact local-model calibration identity, and emits explicit repair, calibration, external
approval, or human-review routes. It performs no inference and cannot rank candidates. See
[`sprint25-verification-routing.md`](sprint25-verification-routing.md).

The license analysis, live H22.0.368 Apprentice inventory, World Seed Atlas brief, plugin risk
matrix, Labs/MOPs acceptance gates, and Sprints 19–24 are maintained in
[`apprentice-creative-expansion-plan.md`](apprentice-creative-expansion-plan.md).
