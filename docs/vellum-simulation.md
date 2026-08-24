# Bounded Vellum simulation

Sprint 7 adds the first stateful simulation lane: `sop.vellum_relic_drop@1.0.0` and
`simulate.vellum_relic_drop@1.0.0`. The workflow is deliberately small enough for Apprentice and
local iteration, but its contracts apply to later Vellum, RBD, Pyro, and FLIP skills.

## Graph contract

The recipe is a readable native-SOP graph. It contains no Python SOP, generated VEX, or UI-state
dependency.

| Contract | Meaning |
| --- | --- |
| `OUT_<RUN>_REST` | Closed, time-independent polygon source before constraints |
| `OUT_<RUN>_CONSTRAINTS` | Combined cloth and pressure constraint geometry |
| `OUT_<RUN>_COLLIDER` | Closed floor collider connected to solver input 2 |
| `OUT_<RUN>_SIM_RAW` | Uncached Vellum Solver output |
| `OUT_<RUN>_CACHE` | File Cache boundary, passing its input until separately saved |
| `OUT_<RUN>_COMPARE` | Rest and simulated states beside the collider for human inspection |

The solver receives corresponding simulation geometry and constraints on inputs 0 and 1 and the
explicit collider on input 2. The constraint chain combines Cloth with Pressure so the object can
deform on impact while maintaining the closed piece's volume. Solver substeps, constraint
iterations, smoothing iterations, gravity, source shape, mass, thickness, and frame range remain
editable parameters rather than hidden constants.

The pinned API source is the official SideFX documentation for [Vellum Constraints](https://www.sidefx.com/docs/houdini/nodes/sop/vellumconstraints.html),
[Vellum Solver](https://www.sidefx.com/docs/houdini/nodes/sop/vellumsolver.html), and
[File Cache](https://www.sidefx.com/docs/houdini/nodes/sop/filecache.html). Exact operator and
parameter tokens are integration-tested against Houdini `22.0.368`.

## Temporal cook contract

`cook.node` and `cook.job.submit` now accept `scope: frame_range` with an inclusive
`frame_range: [start, end, step]`. Before creating a job the controller verifies:

- finite start, end, and step values;
- positive step and non-decreasing range;
- exact expanded frame count at or below `policy.max_frames`;
- declared point, primitive, memory, and total-seconds estimates within policy.

The main-thread runner evaluates frames in order inside one total timeout, records geometry and
elapsed time for every frame, aggregates peak topology/memory for budget checks, attaches frame
numbers to node messages, and restores the original global frame even on failure. The JSONL
`finished` record contains `frame_metrics`, so simulation validation does not depend on leaving
the artist's timeline at the last simulated frame.

The bundled skill caps one run at 48 frames and uses a 24-frame preview by default. Its temporal
cook targets `OUT_<RUN>_CACHE`, proving actual simulated motion rather than allowing the static
rest/collider comparison bounds to mask it.

## Cache policy

The recipe configures a versioned `.bgeo.sc` sequence beneath `artifact_dir/cache/<run>/v001/`,
sets the requested frame range, enables simulation initialization, and leaves **Load from Disk**
off. Instantiating or cooking the skill never presses **Save to Disk**. This distinction matters:
graph creation and in-memory verification are medium/low-risk operations, while writing a full
sequence needs a separate explicit output, capacity, and overwrite decision.

The graph manifest records cache status as `configured_not_written`. Existing cache files are
therefore neither trusted nor replaced implicitly.

## Skill use

Load `skills/simulate.vellum_relic_drop` through the ordinary skill loader and call `plan` with an
existing SOP network path plus an absolute artifact directory. The returned commands perform:

1. approved transactional recipe instantiation with checkpoint and replay log;
2. bounded inclusive frame-range cook with per-frame metrics;
3. read-only rest and collider validation;
4. deterministic graph SVG and manifest capture;
5. optional explicit-camera 1280×720 final-frame viewport capture;
6. incremented `.hipnc` snapshot.

No aesthetic winner is chosen. The rest/simulation comparison remains editable for a human or a
later creative-review stage.

## Failure and continuation

A run is refused before mutation when its range expands beyond 48 frames. Existing exact contract
names cause transactional rollback. Observed budget overruns and Houdini errors fail the cook and
remain in the durable log. Partial caches are not deleted because this skill never creates them.

For refinement, branch from a named contract or duplicate the recipe with a new run ID. Increase
substeps for fast collisions, increase constraint iterations for stiff constraints, and keep the
File Cache boundary before escalating to longer sequences. A human can continue entirely in the
native node graph.
