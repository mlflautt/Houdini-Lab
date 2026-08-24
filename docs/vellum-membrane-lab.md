# Vellum membrane laboratory

Sprint 13 extends the single-object Sprint 7 Vellum controller into a comparable material study:
`sop.vellum_membrane_lab@1.0.0` and `simulate.vellum_membrane_lab@1.0.0`. Three independent native
Vellum branches—silk, rubber, and reinforced—share one rest topology and collider contract without
sharing simulation state or implying an aesthetic winner.

## Graph and material contract

One ZX Grid and explicit Group Create node define a polygon sheet with a named `anchors` edge. Each
candidate applies a seed-derived native Mountain perturbation, then Cloth and permanent Pin to
Target constraints. Silk uses very soft bend, rubber uses more compliant stretch and stronger bend,
and reinforced adds Surface Struts over its Cloth and Pin layers. Each terminal constraint graph
feeds its own Vellum Solver and non-writing File Cache boundary.

The implementation follows SideFX's [Vellum Constraints](https://www.sidefx.com/docs/houdini/nodes/sop/vellumconstraints.html)
contract: Vellum configuration consists of matching simulation geometry and explicit constraint
geometry. The three solvers receive those as inputs 0 and 1, plus the shared sphere-and-floor
collider on input 2 as required by the [Vellum Solver SOP](https://www.sidefx.com/docs/houdini/nodes/sop/vellumsolver.html).
The solver remains in Full/Dynamic mode because pins and polygon collision are intentional features.

Live Houdini 22.0.368 probing established two source-of-truth details:

- A Pin node must use the main `grouptype=points`, `group=anchors` contract. Populating only its
  secondary `pingroup` field zeroed mass on every point and silently froze the entire membrane.
- Ordinary Struts generated no additional constraints on the open Grid. Surface Struts increased
  the 25×25 reinforced fixture from 3,456 to 6,838 constraint primitives without warnings.

These are asserted behaviorally, not inferred from parameter round-trips.

## Temporal and cache verification

`simulate.membrane.validate` checks exact types, roles, connections, solver/material parameters,
cache paths, comparison order, and separate labels before cooking. At every frame it records each
candidate's topology, bounds, centroid, memory, Houdini messages, and cook time. Final checks require:

- exactly one `resolution`-sized edge at zero mass and all other points at declared mass;
- anchor drift below 0.02 Houdini units;
- average dynamic-point displacement above 0.25;
- materially more reinforced constraints than either base Cloth profile;
- three spatially distinct final states;
- selected and comparison topology matching their human Switch contracts.

The default is 24 frames and the hard ceiling is 48. Combined candidate geometry stays below
75,000 points/primitives and 512 MiB. File Cache nodes remain `loadfromdisk=0`; neither the skill nor
validator presses Save to Disk, deletes partial data, or trusts a stale cache.

The final 24-frame Houdini 22.0.368 acceptance run validated in 16.22 seconds. All candidates kept
zero anchor drift and averaged 1.35–1.39 Houdini units of dynamic-point displacement. The 768×432
Karma CPU comparison retained three readable silhouettes and passed the deterministic exposure,
occupancy, three-panel, edge, and two-percent crop-margin checks with no flags. The corresponding
critique packet records the render, graph, manifests, recipe, skill, validator, and this document;
inference remains deliberately unperformed.

## Visual and model verification

An explicit GUI viewport capture may feed `visual.analyze` and a hashed multimodal critique packet.
The deterministic gate catches blank, exposure, occupancy, panel, crop, and duplicate failures
before a model is involved. Model inference remains a separately approved advisory action and may
not populate `winner` or human ratings. Apprentice Karma proof, when separately requested, stays at
or below 1280×720 and must be checked for watermark overlap.

## Continuation

Artists can edit each material's Cloth, Pin, Surface Struts, Solver, or rest-shape nodes directly.
Longer simulations and actual cache writes remain separate resource decisions. Future work may add
painted stiffness, animated targets, stitched multi-panel garments, or calibrated local-VLM motion
critique, but those should compose around these named contracts instead of hiding behavior in a
Python SOP.
