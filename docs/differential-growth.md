# Native differential growth

Sprint 9 turns the differential-growth pattern into a bounded graph-first capability:
`sop.differential_growth_loop@1.0.0` and `generate.differential_growth@1.0.0`. It follows the
opposing-force construction demonstrated in SideFX's
[Complex Growth in 2 Nodes](https://www.sidefx.com/tutorials/complex-growth-in-2-nodes/) while
keeping the full native network editable and inspectable.

## Graph contract

The outer SOP recipe preserves three unranked source branches:

| Switch input | Candidate | Contract |
| --- | --- | --- |
| 0 | circle | closed, symmetric control case |
| 1 | ellipse | closed default fixture; anisotropy encourages visible folds |
| 2 | spiral | open curve; self-proximity produces a different growth family |

The source Switch feeds a small seeded Mountain perturbation and initial Resample. These create a
reproducible symmetry break and common point spacing without embedding generated code. The selected
curve branches into `OUT_<RUN>_REST_CURVE` and the native Solver.

The checkpointed `growth.solver.populate` tool accepts only an exact pristine `solver` SOP. It
opens the built-in editable `d/s` SOP Solver network and changes this default connection:

```text
Prev_Frame ─────────────────────────────────────────────→ OUT
```

into the registered feedback graph:

```text
Prev_Frame → HERMES_POINT_SEPARATION (Relax)
           → HERMES_CURVE_RELAX (Attribute Blur P)
           → HERMES_EDGE_SPACING (Resample)
           → OUT
```

Point Relax separates nearby curve points. Attribute Blur uses mesh connectivity to oppose that
expansion by smoothing `P`. Resample restores a consistent segment scale after each feedback step.
The raw result remains available as `OUT_<RUN>_GROWTH_CURVE`; PolyWire creates
`OUT_<RUN>_GROWTH_WIRE`; translated rest/grown surfaces merge into
`OUT_<RUN>_COMPARE`. HOM creates, connects, parameterizes, and tags these nodes but never iterates
over geometry. The node graph remains the executable artifact.

Pinned references:

- [Attribute Blur SOP](https://www.sidefx.com/docs/houdini/nodes/sop/attribblur.html)
- [Point Relax SOP](https://www.sidefx.com/docs/houdini/nodes/sop/relax.html)
- [Resample SOP](https://www.sidefx.com/docs/houdini/nodes/sop/resample.html)
- [PolyWire SOP](https://www.sidefx.com/docs/houdini/nodes/sop/polywire.html)

Exact types, parameter names, menus, and editable Solver paths are integration-tested against
Houdini `22.0.368` rather than inferred from a tutorial screenshot.

## Temporal and resource contract

The default run evaluates frames 1–24 inclusively. One `cook.node` frame-range job records point,
primitive, bounds, memory, elapsed time, warnings, and errors for every frame, then restores the
artist's original frame. Hard skill limits are:

- 24 frames;
- 50,000 points and 50,000 primitives at every frame;
- 512 MiB estimated memory;
- 90 seconds total;
- in-memory Solver caching only (`cachetodisk=0`).

The tested ellipse fixture stays compact through the early expansion and enters a high-fold regime
late in the range. The ceiling is intentionally close enough to reject runaway parameter choices
before they become an accidental production simulation. A longer range, smaller segment length,
larger Point Relax radius, disk cache, PDG variation run, or final render is a separate resource
decision.

## Evidence and human continuation

A normal run produces two checkpoints, replayable outer-graph and solver-population JSONL logs, a
per-frame cook log, rest-curve validation, outer and inner graph SVGs, a graph/provenance manifest,
and an incremented `.hipnc` snapshot. Candidate entries contain stable IDs, the common seed,
lineage, empty human-rating fields, and no automatic rank. The Switch controls only the previewed
source and never deletes alternatives or implies a winner.

Visual proof follows the same separation as Sprint 8: an explicit GUI viewport may be requested by
named viewer, viewport, and camera, or `lookdev.relic_stage` may import the grown wire and perform a
separately approved one-frame Karma CPU render. Apprentice output remains at or below 1280×720.

## Failure and rollback

The population tool checkpoints before touching the Solver and refuses a non-pristine feedback
output instead of replacing artist work. Any partial managed-node creation is destroyed and the
original `Prev_Frame → OUT` connection is restored. Outer exact-name collisions roll back through
the ordinary recipe transaction. No operation writes a geometry cache, launches a background
process, installs SideFX Labs, or executes arbitrary VEX/Python.

## Verified Sprint 9 evidence

The accepted live fixture uses Houdini `22.0.368` Apprentice, ellipse input 1, seed `2401`, and the
default 24-frame solver settings. Its comparison output grows from 632 points/primitives at frame 1
to 24,964 at frame 24, with 6,182,784 bytes of reported geometry memory and no Houdini warnings or
errors. All 24 per-frame records remain below both 50,000 topology ceilings.

The presentation proof imports the unchanged frame-24 grown wire into the Sprint 8 Solaris lane,
binds the amber MaterialX candidate, and renders through `BRAY_HdKarma` at 640×360 in 8.62 seconds.
The image is 216,055 bytes. The wider front camera is explicitly recorded as a presentation-only
change; the manifest says `geometry_changed: false` and points back to the source growth manifest.

Local artifacts are kept under `.hermes/sprint9-live-2/` for the accepted growth run and
`.hermes/sprint9-live-3/` for the final visual proof. The earlier tight-framing attempts remain in
place as failed visual evidence rather than being overwritten.
