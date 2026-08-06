# Graph recipes

A **recipe** is a versioned, declarative description of a subgraph that Hermes can
instantiate with exposed variables. Recipes are the normal mid-level interface: more
stable and reusable than raw node creation, lighter than a full HDA.

## Format (YAML)

```yaml
id: sop.scatter_cluster_points
version: 1.0.0
summary: Scatter N points on a surface with attribute noise.
contexts: [SOP]
inputs:
  parent_path: {type: string}
  count: {type: integer, min: 1, max: 1000000, default: 1000}
  seed: {type: integer, default: 42}
nodes:                       # ordered create list
  - {id: src, type: scatter, name: SCATTER_PTS, params: {force_total: "{{count}}"}}
outputs:
  - SCATTER_PTS
```

## Conventions
- `id` is `<context>.<snake_name>`; `version` is semver.
- Reference nodes by the local `id` in connections/outputs.
- Keep `contexts` explicit (SOP/OBJ/LOP/...).
- Pin any SideFX Labs dependency in `meta.depends`.

See `docs/architecture.md` §5.3 / §10 for the tool/recipe/skill/HDA distinction.
