# Art-directed RBD fracture

Sprint 17 adds `sop.rbd_art_directed_fracture@1.0.0` and
`simulate.rbd_art_directed_fracture@1.0.0`: a bounded destruction lane that keeps impact art
direction, material fracture, constraints, proxy simulation, transform caching, reconstruction,
and visual presentation separately attributable.

The graph is native and pinned. Houdini 22.0.368 live inspection showed that the unversioned
Material Fracture alias can expose a legacy one-output interface, so the recipe names
`Sop/rbdmaterialfracture::4.0` exactly. That definition exposes Geometry, Constraint Geometry, and
Proxy Geometry outputs. HOM creates and verifies the graph; native SOPs perform all geometry and
simulation work.

## Graph contracts

```text
SOURCE_BOX -> POLYBEVEL -> NORMALS -> OUT_SOURCE -------------------+
                                                                    |
RADIAL_SPHERE -> SCATTER(8)  -> OUT_IMPACT_RADIAL ----+             |
OFFSET_SPHERE -> SCATTER(12) -> OUT_IMPACT_OFFSET ----+-> SWITCH ---+-> MATERIAL_FRACTURE::4.0
TOP/BOTTOM SPHERES -> SCATTER(6+6) -> OUT_IMPACT_LAYERED +              | geometry | constraints | proxy
                                                                          +--------+-------------+------+
                                                                                   v
                                                                              RBD_CONFIGURE
                                                                                   v
                                                                             BULLET_SOLVER
                                                                  geometry / constraints / Simulation Points
                                                                                               |
                                                                                     TRANSFORM_FILE_CACHE
                                                                                       configured, unwritten
                                                                                               |
REST_PIECES -----------------------------------------------------------> TRANSFORM_PIECES <------+-- TIME_SHIFT(start)
                                                                               |
                                                                             AFTER

OUT_SOURCE -> BEFORE_LAYOUT --+
                               +-> BEFORE_AFTER_MERGE -> OUT_COMPARE
AFTER ------> AFTER_LAYOUT ----+
```

The three impact profiles are retained as editable graph branches in fixed `radial`, `offset`,
`layered` order. The Switch is a human preview choice, not an aesthetic rank. Seeds, point counts,
empty human ratings, null winner, and disabled automatic ranking are recorded in the graph
manifest.

## Transform cache contract

The Bullet Solver's fourth output is the compact **Simulation Points** representation. On the
pinned build it carries one point per named piece with `P`, `orient`, `pivot`, `scale`, `v`, and
`w`. Sprint 17 places a File Cache on that output rather than on duplicated polygon geometry.
Load from Disk remains off and the skill never presses Save to Disk. Its frame range is written as
safe constant HScript expressions because the File Cache HDA ships with `$FSTART/$FEND`
expressions that a literal HOM assignment intentionally preserves.

Transform Pieces receives:

1. editable polygon rest pieces;
2. current cached Simulation Points;
3. the same transform stream frozen at the declared start frame.

This proves the same compact data contract a later Solaris RBD procedural can consume without
making USD staging or rendering a hidden side effect of the simulation skill.

## Safe default and permission boundary

- one selected impact profile is fractured and simulated;
- 48 inclusive frames, one-frame step;
- no more than 5,000 named pieces;
- native proxy geometry and one in-process Bullet Solver;
- five Bullet substeps and ten constraint iterations by default;
- 512 MB Houdini simulation-cache setting and 1 GiB command memory ceiling;
- 250,000-point and 250,000-primitive reconstruction ceilings;
- no external processes, background work, VEX, Python SOPs, network access, or plugin install;
- configured transform cache only—writing a `.bgeo.sc` sequence remains a separate decision;
- optional preview at or below the Apprentice 1280×720 ceiling;
- full-resolution fracture, longer simulation, disk-cache execution, Solaris stage, and final
  render remain separately approved operations.

The recipe transaction saves an incremented `.hipnc` checkpoint before graph edits. It refuses
name collisions and existing artifact files instead of overwriting them.

## Validation

`simulate.rbd.validate` checks the composed result rather than trusting UI or parameter readback:

1. exact managed node types, roles, paths, three-output fracture version, and wiring;
2. fixed impact profile order and exact 8/12/12 point counts;
3. unique primitive `name` values and the 5,000-piece ceiling;
4. material constraint `constraint_name`, `constraint_type`, and `strength` attributes;
5. packed RBD Configure and explicit active-piece contract;
6. Bullet ground, start frame, substeps, iterations, break behavior, and cache-memory setting;
7. every frame's stable unique name set and finite transform attributes;
8. deterministic SHA-256 over each ordered transform set;
9. Transform Pieces preservation of rest topology and piece names;
10. meaningful vertical motion and at least one broken material constraint;
11. bounded topology, memory, cook time, and clean Houdini messages;
12. no transform-cache files written and restoration of the caller's timeline frame.

`OUT_COMPARE` keeps the intact source and reconstructed result side by side. Font labels live on a
separate output and never enter render geometry. Optional capture follows the repository's
[verification ladder](verification-ladder.md): deterministic image mechanics first, then a hashed
advisory critique packet. No model is downloaded or run implicitly, and no critique can fill the
winner or human-rating fields.

## Artifacts

One successful run creates new files beneath its artifact root:

```text
checkpoints/   incremented pre-recipe .hipnc
logs/          replayable graph-batch JSONL
manifests/     every-frame RBD validation, graph metadata, optional visual/critique JSON
observations/  selection-free graph SVG and optional before/after PNG
scenes/        incremented final .hipnc snapshot
cache/         declared transform path only; absent until a separate approved cache write
```

## Houdini 22.0.368 acceptance

The initial pinned Apprentice acceptance used the `radial` profile and completed all 48 frames.
It produced 25 stable named pieces and 89 material constraints; all 89 broke during the proxy drop.
The transform centroid dropped 3.819992 units. Every frame retained the same piece names and a
64-character transform SHA-256, Transform Pieces retained rest topology, no managed node emitted a
warning or error, the timeline was restored, and the configured cache wrote no files.

Visual acceptance retained two diagnostic camera attempts: the initial proof cropped the debris at
the bottom, and the first wider pitch clipped the intact monolith at the top. Deterministic image
analysis flagged both without making an aesthetic choice. The accepted `sprint17_wide3` 768×432
Karma CPU proof has no mechanical flags, preserves both panels, keeps the combined subject inside
`[223, 76, 734, 395]`, and records SHA-256
`06c0d031df484139e94639a798d208a8b54ae7ec4d8e1a017c42198a5ffb1536`. Its critique packet is
advisory and performs no inference. Evidence lives under `.hermes/sprint17-live/`.

## References

The composition follows SideFX's
[Introduction to Material-Based Destruction](https://www.sidefx.com/docs/houdini/destruction/tutorials/intro_to_mbd_1.html)
and [Violin RBD Shatter](https://www.sidefx.com/tutorials/violin-rbd-shatter/) examples. Operator
contracts follow the official [RBD Material Fracture](https://www.sidefx.com/docs/houdini/nodes/sop/rbdmaterialfracture.html),
[RBD Bullet Solver](https://www.sidefx.com/docs/houdini/nodes/sop/rbdbulletsolver.html), and
[Transform Pieces](https://www.sidefx.com/docs/houdini/nodes/sop/xformpieces.html) documentation.
Houdini 22's [RBD updates](https://www.sidefx.com/docs/houdini/news/22/rbd.html) and the Solaris
[Houdini RBD Procedural](https://www.sidefx.com/docs/houdini/solaris/houdini_rbd_procedural.html)
define the later transform-to-USD extension boundary.
