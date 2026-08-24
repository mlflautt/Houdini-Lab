# Native L-System botanical grammars

Sprint 11 implements a bounded, graph-first botanical grammar capability. The source of truth is
`sop.lsystem_botanical@1.0.0`; `grow.botanical_grammar@1.0.0` checkpoints, instantiates, cooks,
validates, observes, and snapshots that native SOP graph. HOM never iterates points or expands the
grammar. Houdini's L-System SOP performs rewriting and turtle geometry; PolyWire performs the
curve-to-surface work.

## Registered candidates

Safe mode contains three exact, versioned templates in fixed order:

1. `canopy` — a three-way 3D crown using yaw, pitch, and roll branching.
2. `fern` — a planar recursive stem-and-frond grammar with an `F=FF` edge rule.
3. `coral` — a radial five-way grammar with yaw, pitch, and roll branches.

Each premise begins with the documented `a("Cd",...)` turtle command. Point Attributes are enabled,
so the skeleton contracts expose `P`, `Cd`, `width`, `arc`, `gen`, and `up`. Deterministic Random
Scale changes lengths without changing topology, using recorded candidate seeds `seed`, `seed+101`,
and `seed+211`.

Every skeleton feeds a three-division PolyWire whose radius is scaled by `width`. The registered
turtle thickness starts at `1.0`; relying on Houdini's `0.1` default made the first visual proof ten
times thinner than intended. The three wires feed a human Switch and separate comparison
Transforms. Merge order is canopy, fern, coral, followed by one explicit framing Transform. No
candidate is deleted, rated, or declared the winner.

## Safe grammar boundary

The public interface exposes only seed, one-to-six generations, wire radius, and the Switch input.
It does not accept premise/rule strings, generated VEX, Python SOP code, or a rule-file path.
`botanical.validate` checks:

- exact L-System type, managed role, embedded premise, enabled productions, parameter values,
  deterministic candidate seed, skeleton mode, and disabled rule-file IO;
- exact L-System → PolyWire → named Null branch structure and width-aware PolyWire controls;
- fixed Switch and comparison order plus the registered placement/framing transforms;
- non-empty finite geometry, no Houdini warnings/errors, distinct skeleton topology, required
  point attributes, generation/arc ranges, memory, elapsed time, and combined point/primitive
  ceilings;
- an absolute new JSON evidence path, with no overwrite.

The original roadmap allowed up to eight generations. The implemented safe ceiling is six because
the coral production contains five recursive `A` symbols. At six generations the conservative
estimate is 67,212 wire points and 134,424 wire primitives; at seven, the primitive estimate would
cross the shared 250,000 ceiling.

## Verified Sprint 11 evidence

The structural acceptance run used the public default: seed 4103, six generations, wire radius
0.018, and human preview input 0 in Houdini 22.0.368 Apprentice.

- Graph: 17 native SOP nodes and 18 wires; no Python SOP, Attribute Wrangle, rule-file IO, or Labs
  dependency.
- Skeleton topology: canopy 366/364, fern 1,331/243, and coral 3,907/3,906 points/primitives.
- PolyWire topology: canopy 1,945/3,163, fern 4,477/7,138, and coral 40,826/81,516.
- Combined comparison: 47,248 points, 91,817 primitives, and 278,118 vertices.
- Observed geometry memory: 21,135,908 bytes; validation elapsed time: 0.311 seconds.
- Every skeleton carried the required turtle attributes with finite bounds and no node messages.
- Graph SVG, graph/geometry manifests, replay log, and versioned `.hipnc` snapshot are under
  `.hermes/sprint11-default6/`.

The accepted visual proof used five generations and wire radius 0.025 so the inherited Sprint 8
lookdev lane remained a separately attributable, inexpensive preview. It produced 10,242 comparison
points and 19,639 primitives, then composed a 28-prim USD stage and rendered one 768×432 Karma CPU
frame in 6.581 seconds. Evidence is under `.hermes/sprint11-live-4/`.

Earlier proofs are intentionally preserved under `.hermes/sprint11-live/` through
`.hermes/sprint11-live-3/`. They exposed thin default width, crowded placement, and watermark/frame
collisions. Those observations drove the explicit registered thickness, candidate placement, and
uniform framing contract now covered by pure and Hython tests.

## References

- SideFX: [L-System SOP](https://www.sidefx.com/docs/houdini/nodes/sop/lsystem)
- SideFX: [L-Systems Node lesson](https://www.sidefx.com/tutorials/l-systems-node/?collection=63)
- SideFX: [PolyWire SOP](https://www.sidefx.com/docs/houdini/nodes/sop/polywire.html)

The optional [Labs Curve Branches SOP](https://www.sidefx.com/docs/houdini/nodes/sop/labs--curve_branches.html)
remains outside this baseline. It would require a separately approved and pinned SideFX Labs
installation rather than silently changing this dependency-free fixture.
