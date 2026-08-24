# MPM matter sculpture

Sprint 14 introduces `sop.mpm_matter_sculpture@1.0.0` and
`simulate.mpm_matter_sculpture@1.0.0`: a proxy-first native Houdini 22 MPM study in which three
material behaviors collide in one editable simulation. It follows SideFX's documented
[MPM workflow](https://www.sidefx.com/docs/houdini/mpm/workflow.html) while keeping graph creation,
simulation, surfacing, caching, and rendering separately attributable.

## Graph and material contract

Three polygon spheres receive deterministic native Mountain perturbations, then feed exact MPM
Source SOPs. Their fixed order is granular-like, elastic-like, and viscous-like. Each Source has a
direct second-input wire from the shared MPM Container; the static MPM Collider receives the same
Container. The merged Sources, Collider, and Container connect to MPM Solver inputs 0, 1, and 2.

The behavioral names are creative starting points, not calibrated physical identities. Houdini
22.0.368 exposes sand, jello, honey, and other entries through a callback-driven Material Preset
menu. As with the repository's Copernicus preset boundary, a menu value alone does not prove that
its coefficient callback ran. The recipe therefore stores constitutive behavior, density,
stiffness/incompressibility exponent tokens, volume preservation, viscosity/plasticity, and sand
friction/cohesion explicitly. Live probing also established that the direct Viscosity parameter
clamps at `1.0`; the registered viscous-like profile uses `0.85` and exact validation rejects an
inert out-of-range request.

The Solver is deterministic, uses adaptive substeps, retains a bounded 1024 MB in-memory cache,
and disables disk checkpoints. Its output passes through a File Cache configured with
`filemode=none`, `loadfromdisk=0`, and an explicit project artifact path. Named particle and native
MPM Surface contracts feed a human-editable Switch. Selecting a surface is an output decision, not
an aesthetic ranking of the material profiles.

## Proxy, temporal, and interruption contract

The normal skill permits at most 24 inclusive frames and 150,000 particles. A conservative source
volume estimate must pass before graph mutation. The roadmap's one-million-particle ceiling, any
geometry cache write, and a final render are independent resource approvals.

Before simulation, the validator cooks each Source and proves finite bounds, point count, explicit
density, and estimated mass. On every Solver frame it records:

- point, primitive, vertex, memory, attribute, group, and bounds metrics;
- a bounded finite position/velocity sample, centroid, and maximum speed;
- all three material source identities and their particle counts;
- estimated total source mass plus exported start-frame, substep, voxel, grid-scale, and particle-
  separation detail values;
- node messages and cook duration.

Final checks require measurable temporal motion and a selected output matching the registered
particle or surface contract. The original artist frame is restored even on failure.

The cache-progress manifest is created before the first frame and atomically rewritten after each
completed frame. It records planned/completed frames, current status, timestamps, the configured
cache path, and whether cache writing is enabled. Exceptions convert it to `failed`; successful
validation converts it to `complete`. This does not pretend partial geometry was cached—the File
Cache remains non-writing—but it gives a future isolated cache worker an interruption-safe resume
contract rather than an ambiguous directory scan.

## Visual and model verification

Optional explicit-camera viewport evidence runs through deterministic blank, exposure, occupancy,
crop, and panel checks before a hashed multimodal critique packet can be produced. Model inference
remains separate and advisory: it cannot populate a winner or human rating. A separately approved
Apprentice Karma proof stays at or below 1280×720 and must be evaluated for watermark overlap.

## Continuation

Artists can edit the three source meshes and Mountain nodes, every material coefficient, the tilted
VDB collider, Container resolution/domain, Solver forces/substeps, surfacing controls, cache path,
and output Switch. Larger cache jobs should reuse the durable progress schema in an isolated
process group rather than silently broadening this safe in-process proxy validator.

## Live Houdini 22.0.368 acceptance

The final 24-frame Apprentice acceptance used particle separation `0.12`. Granular, elastic, and
viscous Sources produced 542, 549, and 552 points with estimated masses 1404.864, 996.1056, and
1192.32 respectively. Frame 24 retained all 1,643 particles, used four adaptive substeps, occupied
226,916 bytes of reported geometry memory, and moved the sampled centroid 1.795075 Houdini units
from the start frame. Exact temporal validation completed in 2.80 seconds after OpenCL kernels were
available. The progress manifest contains every frame 1–24 with `status=complete`; no geometry cache
directory was created.

Visual refinement was evidence-driven and preserved rather than hidden. The first 768×432 Karma
CPU proof warned `possible_crop` because the sculpture touched the top boundary. Raising the camera
too far cleared that mechanical warning but crowded the Apprentice watermark. A midpoint camera
height produced the final proof in `.hermes/sprint14-live-3`: 23.0% occupied pixels, 53-pixel top
margin, no visual flags, and a deterministic `pass`. The critique packet hashes the render, both
graph manifests, simulation/progress validation, visual report, recipe, skill, validator, and
replayable acceptance script; inference remains deliberately unperformed.

Repository gates finish at 103 collected unit tests (99 passed and four optional-runtime skips),
31 Hython/HDA integration tests, full Ruff lint/format checks across 118 files, and an isolated
`0.15.0` wheel smoke test exposing 46 tools, 11 recipes, one HDA, and 11 discoverable skills.
