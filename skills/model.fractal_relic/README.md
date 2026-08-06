# model.fractal_relic

**Radial fractal relic generator.** Builds a seeded, parameterized alien-relic form from
native SOP nodes (sphere → scatter → copy-to-points → named output). Deterministic by seed.

## Controls
- `seed` (int) — deterministic variation
- `iterations` (1–8) — detail density scaler
- `detail_level` (draft | preview | final) — cook budget tier

## Verification
- Graph: named `OUT_GEO`, no node errors, branches end in nulls.
- Data: finite bounds, no NaN positions, point count < budget.
- Visual: readable silhouette, hierarchical branching, seed determinism.

## Apprentice note
Non-commercial. Renders capped at 1280×720, watermarked. HDA (if promoted) stays `.hdanc`
and cannot be used with Houdini Engine.
