# Conventions

Quick reference for graph/naming/attribute conventions (full detail: `docs/architecture.md` §7).

## Top-level contexts
```
/obj   HERMES_ASSET_<name>  HERMES_SHOT_<name>  IMPORTS  REFERENCES
/stage HERMES_STAGE_<name>
/tasks HERMES_PDG_<name>
/out   HERMES_OUTPUT_<name>
```

## SOP Null contracts
`IN_GEO` `IN_POINTS` `IN_COLLISION` `OUT_GEO` `OUT_PROXY` `OUT_RENDER` `OUT_COLLISION` `OUT_DEBUG`

## Network boxes
`INPUT` `PREP` `GENERATE` `SIMULATE` `POST` `MATERIAL` `CACHE` `OUTPUT` `DEBUG`

## Naming
`SRC_BASE_MESH` `ATTR_VARIATION` `SCATTER_PRIMARY` `COPY_INSTANCES` `VELLUM_CONFIG`
`CACHE_PRE_SIM` `OUT_RENDER` `LOP_COMPONENT_BUILD` `TOP_WEDGE_VARIANTS`

## Attribute contract (default)
```
point:  id, pscale, orient, Cd, variant
primitive: name, material
```
Do not casually overwrite `N`, `v`, `orient`, `name`, `id`, `class`, `material`.

## Paths
- `$JOB` = project root; use project-relative paths.
- `$HIP` only for assets truly relative to the current scene.
- Never absolute user-specific paths inside HDAs/HIPs.
