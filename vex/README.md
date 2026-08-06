# Approved VEX templates

Curated, reviewable VEX snippets used by `vex.instantiate_template` / `vex.set_template_variables`.
Do NOT expose unrestricted `set_wrangle_code` as a normal tool (docs §10.7, §11.4). Each
template declares attributes used + variables so validation can check it.

| Template | Purpose |
|----------|---------|
| `deterministic_random` | stable hashed per-point random from seed |
| `orient_setup` | build quaternion orientation from normal |
| `attribute_remap` | remap an attribute through a ramp |
| `growth_mask` | radial growth bias field |
| `color_variant` | assign variant color from id |
