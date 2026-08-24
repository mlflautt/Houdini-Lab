# Sprint 21 — Labs-enhanced World Seed Atlas

Sprint 21 turns Sprint 20's three certified SideFX Labs nodes into optional production branches
inside the native World Seed Atlas. The native skill remains the source; every world receives one
separate overlay selected by an explicit `labs_available` input.

## Graph contract

For Amber Mesa, Verdant Rift, and Lunar Basin, the overlay uses:

- `labs::terrain_analysis::1.0` for slope and horizontal-curvature cartography before a native
  HeightField-to-mesh boundary;
- `labs::instance_attributes::1.0` for deterministic `orient`, `pscale`, and `scale` before native
  Copy to Points;
- `labs::measure_curvature::3.1` for convexity/concavity treatment of the hero artifact.

The complete enhanced world and the unmodified native world feed a Switch whose saved default is
input zero, native. A separate Merge preserves both in the render comparison. No branch is renamed
best, no score is synthesized, and all human-rating slots remain empty.

When `labs_available=false`, Hermes instantiates `sop.world_seed_labs_unavailable@1.0.0`. That
recipe contains no Labs types, creates `OPTIONAL_LABS_UNAVAILABLE`, and keeps native geometry
cookable and renderable. Capability choice is therefore replayable input data rather than an
implicit lookup during graph mutation.

## Live acceptance

Houdini 22.0.368 Apprentice produced 4,734 points and 4,440 primitives across three native/Labs
pairs. The 768x432 Karma CPU proof has six present panels, crop-safe margins, no mechanical visual
flags, and SHA-256 `764210b...dc51`.

A separate launch with `HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json` loaded the skill in bare
Hython without PyYAML, instantiated no plugin nodes, created all three unavailable markers, and
cooked the native 2,442-point/2,292-primitive Atlas successfully.

Evidence:

- compact record: `plugins/evidence/labs-atlas-acceptance-22.0.368.json`
- local enabled run: `.hermes/sprint21-acceptance-20260824-c/`
- local plugin-disabled run: `.hermes/sprint21-native-fallback-20260824-a/`
- saved scene: `labs_world_seed_atlas_sprint21_live_final_v001.hipnc`

The visual system proves presence, exposure, crop safety, and nonblank output. It does not decide
whether native or Labs treatment is aesthetically preferable.
