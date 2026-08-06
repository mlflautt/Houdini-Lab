# Skills

A **skill** composes tools and recipes into a creative procedure with planning, validation,
observation, and refinement. A skill = a folder with `skill.yaml` (manifest) + `skill.py`
(module) + `README.md`.

## Manifest (`skill.yaml`)

```yaml
id: model.fractal_relic
version: 0.3.0
summary: Generate a radial fractal relic form from native SOP nodes.
contexts: [SOP]
intent_tags: [organic, growth, alien, procedural]
inputs:
  parent_node_id: {type: string}
  seed: {type: integer, default: 42}
  iterations: {type: integer, min: 1, max: 8, default: 4}
preconditions:
  - parent resolves to a SOP-capable geometry container
risk: medium
checkpoint: before_execute
cook_budget:
  max_points: 3000000
  max_seconds: 90
  max_frames: 1
steps:
  - graph.instantiate_recipe: scatter.cluster_points@1
  - geometry.validate
  - viewport.capture
verification:
  graph_checks: [all major branches end in named null nodes, no node errors]
  data_checks: [finite bounds, no NaN point positions, point count below budget]
  visual_checks: [readable primary silhouette, visible hierarchical branching]
outputs: [output_node_id, graph_manifest_path, preview_path]
rollback: restore_checkpoint
```

## Rules
- Purpose is narrow and documented.
- Contexts + exact Houdini builds declared.
- I/O + attribute contracts explicit.
- Risk + license explicit; checkpoints + rollback exist.
- Seeds reproducible; major stages named/null-contracted.
- Pure logic tested in `tests/unit`; HOM behavior in `tests/hython`.

See `docs/architecture.md` §5.3, §14, §21.
