# Labs-enhanced World Seed Atlas

Sprint 21 composes the native `world.world_seed_atlas` skill with one explicit optional overlay per
world. `labs_available=false` creates `OPTIONAL_LABS_UNAVAILABLE` and never instantiates an unknown
plugin node. `labs_available=true` uses only the three SideFX Labs types certified in Sprint 20.

Native is always Switch input zero and the saved default. The comparison output preserves both
branches with empty human ratings; metrics and visual checks cannot select a winner.
