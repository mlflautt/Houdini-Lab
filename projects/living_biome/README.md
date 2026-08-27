# Living Biome — G002 dry project

This directory is a contract fixture, not a built Houdini scene. `project.yaml` names exact
registered capabilities and four exact adapter records, then preserves Amber Mesa, Verdant Rift,
and Lunar Basin in equal source order with blank human fields.

`motion.particle_calligraphy@1.0.0` is present only as the G002 technical motion fixture. Its
`human_selected_contract` output name is an existing capability contract; it does not mean that a
human selected Particle Calligraphy for G003. The `choose-motion-system` decision remains blank,
and G003 must present viable registered motion options to the owner before freezing its manifest.

The World Seed capability is `world.world_seed_atlas_labs@1.0.0` because its declared
`three_native_worlds` contract exactly matches the audited project adapter. G002 neither enables
Labs nor executes the skill. Native worlds and unavailable-marker fallback behavior remain part of
the capability's own future runtime contract.

Run from the repository root:

```bash
.venv/bin/python scripts/plan_project.py validate \
  --project projects/living_biome/project.yaml \
  --project-root "$PWD"
.venv/bin/python scripts/plan_project.py plan \
  --project projects/living_biome/project.yaml \
  --project-root "$PWD"
```

Both commands are pure and write nothing unless `--output` names a new confined path. A successful
plan is dry contract evidence only: it grants no graph edit, cook, plugin, simulation, render, model,
human, or downstream approval.
