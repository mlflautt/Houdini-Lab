# Procedural district

Sprint 16 adds `top.procedural_district@1.0.0` and
`world.procedural_district@1.0.0`: a bounded local world-building lane that turns a readable
native-SOP massing source into immutable per-lot geometry caches, then assembles those caches into
an editable district and an equal-scale no-winner gallery.

The capability is intentionally self-contained. Sprint 15 terrain remains deferred in this
checkout, so terrain is not a hidden prerequisite. A later terrain integration can replace the
flat ground branch or revise the explicit placement transforms without changing the lot recipe,
cache identities, or PDG execution contract.

## Graph contracts

The registered source recipe `sop.procedural_building_lot@1.0.0` keeps all three massing profiles
visible:

```text
LOT_PLATE ----+------------------+-------------------+
PODIUM -------+-> BLOCK_MERGE ---|                   |
BLOCK_TOWER --+                  |                   |
                                  +-> PROFILE_SWITCH -> POLYBEVEL -> NORMALS -> OUT_BUILDING
TERRACE_WINGS +-> TERRACE_MERGE -|                   |
TERRACE_TOWER +                  |                   |
LOT + PODIUM + NEEDLE_TOWER ----> NEEDLE_MERGE ------+
```

`block`, `terrace`, and `needle` are descriptive silhouette labels, not architectural,
structural, or engineering claims. The native Switch is driven by a declared Wedge attribute;
inactive source branches remain editable. HOM creates, connects, tags, and parameterizes the
graph, while Box, Merge, Switch, PolyBevel, and Normal SOPs perform all geometry computation.

The registered TOP recipe is equally explicit:

```text
                         LOCAL_BOUNDED (one slot)
                                  |
TOP_WEDGE_LOTS -> CACHE_LOT_GEOMETRY -> WAIT_ALL_LOTS -> OUT_LOTS
 declared channels      ROP Geometry TOP
```

There is no Python Processor or Python Script TOP. Fourteen numeric Wedge attributes carry seed,
profile choice, and per-profile width/depth/height/center controls. Channel overrides target exact
native SOP parameters and must leave the source values unchanged after child-process execution.

## Default composition

The safe default generates twelve work items and places them on a four-by-three grid. Each result
retains:

- stable `lot_NNN` candidate ID;
- seed and exact generated controls;
- descriptive profile;
- explicit XYZ placement and Y rotation;
- immutable project-local `.bgeo.sc` path and SHA-256;
- source and TOP recipe versions;
- empty `human_rating` fields;
- `winner: null` and `automatic_ranking: false`.

The assembly graph loads each cache once, adds a profile color as an editable presentation layer,
then branches to an actual district placement and an equal-scale gallery placement. Candidate
geometry inputs are connected before Font labels, preserving an exact `2 × candidate_count`
gallery Merge contract. `OUT_DISTRICT` includes the ground context; `OUT_GALLERY` contains every
candidate and label. Neither output implies a winner.

## Resource and permission boundary

- 12 work items by default; 4–16 accepted by the public skill.
- Exactly one Local Scheduler process slot.
- 30 seconds and 1 GiB declared per worker by default.
- 5,000 points and 5,000 primitives per lot.
- 100,000 primitives and 150,000 points across either assembled presentation branch; the higher
  point allowance accounts for editable Font SOP labels in the gallery.
- 10 MB output allowance per lot within the aggregate command budget.
- One frame per ROP Geometry work item.
- `savebackground=0`; the skill never starts unattended background generation.
- `district.generate` is a static, non-executing manifest pass.
- `district.cook` requires medium-risk approval and
  `policy.allow_external_process=true` before local hython workers may start.
- Existing source networks, TOP networks, manifests, scenes, cache files, assemblies, and images
  are refused rather than overwritten.
- Apprentice/non-commercial output and the 1280×720 preview ceiling remain explicit.

Larger districts, additional scheduler slots, terrain-adaptive placement, detailed facades, USD
instancing, traffic, crowds, multi-frame work, or final renders require a separate resource and
creative decision.

## Validation

`district.validate` verifies the composed result, not only parameter readback:

1. exact native node types and named TOP contracts;
2. one scheduler slot, foreground ROP output, and absence of Python TOPs;
3. result count against the immutable plan;
4. every geometry file's existence, finite bounds, topology budget, file size, and SHA-256;
5. preservation of block, terrace, and needle profiles;
6. district Merge count of `candidate_count + ground`;
7. gallery Merge count of `2 × candidate_count`, with candidates preceding labels;
8. cooked district and gallery topology beyond the raw cache totals;
9. clean Houdini messages;
10. null winner, disabled automatic ranking, and unfilled human ratings.

Selection-free SVG and JSON graph evidence cover source, TOP, and assembly networks. Optional
named-viewport capture passes through deterministic pixel analysis and the existing hashed
multimodal critique packet. Local or external visual models remain advisory and cannot fill a
winner or human rating.

## Artifacts

One successful run produces new files beneath its artifact root:

```text
checkpoints/       pre-build, recipe, and pre-assembly .hipnc checkpoints
geometry/          immutable district_lot_<index>_seed_<seed>.bgeo.sc files
logs/              append-only build, graph-batch, cook, and assembly JSONL
manifests/         plan, result, assembly, validation, graph, optional visual/critique JSON
observations/      source, TOP, and assembly SVGs; optional PNG preview
scenes/            PDG source scene and incremented final .hipnc snapshot
```

Partial cache outputs and explicit failure records are retained for diagnosis. The workflow never
deletes failed evidence or silently retries with a larger budget.

## Houdini 22.0.368 acceptance

The default twelve-lot run completed on Houdini Apprentice 22.0.368 with one Local Scheduler slot.
The PDG cache phase took 56.831 seconds and wrote 87,307 bytes across twelve immutable `.bgeo.sc`
files. The assembled `OUT_DISTRICT` contained 2,696 points and 2,598 primitives with finite bounds
from `[-12.75, -0.1, -9.75]` to `[12.75, 20.8, 9.75]`. The labeled no-winner gallery contained
83,527 points and 2,799 primitives. Block, terrace, and needle profiles were all present; no
managed node reported errors or warnings.

Visual acceptance retained the initial tight crop and three successive camera refinements rather
than overwriting them. The final 768×432 Karma CPU proof uses the same validated district snapshot,
has a subject bounding box `[148, 14, 734, 397]`, 0.291 foreground occupancy, and passes the
deterministic visual gate with no flags. Its hashed advisory critique packet performs no model
inference and records no winner. Evidence lives under `.hermes/sprint16-live/`; the accepted image
is `observations/sprint16_wide4_karma_cpu.png`.

## References

The compositional model follows SideFX's
[Build a City with PDG](https://www.sidefx.com/tutorials/foundations-build-a-city-with-pdg/)
lesson while keeping this implementation smaller and manifest-first. Node behavior follows the
official [Wedge TOP](https://www.sidefx.com/docs/houdini/nodes/top/wedge),
[ROP Geometry Output TOP](https://www.sidefx.com/docs/houdini/nodes/top/ropgeometry.html), and
[Local Scheduler](https://www.sidefx.com/docs/houdini/nodes/top/localscheduler.html) contracts.
