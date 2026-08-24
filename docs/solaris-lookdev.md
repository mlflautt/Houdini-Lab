# Solaris lookdev and bounded Karma preview

Sprint 8 adds the first graph-first USD/lookdev lane. It keeps three resource decisions
separate:

1. `lop.relic_lookdev_stage@1.0.0` creates a readable LOP graph without cooking it;
2. `solaris.stage.validate` explicitly composes one bounded USD stage;
3. `render.karma.preview` launches one separately approved external `husk` process.

The high-level entry point is `lookdev.relic_stage@1.0.0`.

## Editable graph contract

The recipe creates native SOP Import, Material Library, three Assign Material branches,
Switch, Dome Light, Camera, Karma Render Settings, and output Null LOPs. The three assignment
branches remain connected to Switch inputs 0–2. `candidate_index` changes only the previewed
input; it does not delete alternatives, fill rating fields, or imply a winner.

MaterialX builder subnets must live inside the Material Library in Houdini 20 and later. The
narrow `solaris.materialx.populate` tool uses Houdini's pinned builder utility, creates exactly
three subnets, adds native `mtlxstandard_surface` nodes, configures base color/metalness/
roughness, and maps them to explicit `/materials/...` paths. It checkpoints first, refuses
existing exact names, tags managed nodes, and appends replayable JSONL provenance.

References:

- [SOP Import LOP](https://www.sidefx.com/docs/houdini/nodes/lop/sopimport.html)
- [Material Library LOP](https://www.sidefx.com/docs/houdini/nodes/lop/materiallibrary.html)
- [Assign Material LOP](https://www.sidefx.com/docs/houdini/nodes/lop/assignmaterial.html)
- [Camera LOP](https://www.sidefx.com/docs/houdini/nodes/lop/camera.html)
- [Dome Light LOP](https://www.sidefx.com/docs/houdini/nodes/lop/domelight.html)

## USD validation contract

`solaris.stage.validate` is a cook, not a read-only graph inspection. It calls `stage()` on one
explicit LOP output under a prim-count and elapsed-time policy, traverses at most `max_prims`,
checks required asset/material/light/camera/render-settings paths, and computes the selected
asset's USD material binding. It reports prim counts by type, composition time, warnings, errors,
and the resolved material path.

## Karma CPU preview contract

`solaris.karma_rop.build` creates a new editable USD Render ROP under `/out`. It pins the
`BRAY_HdKarma` delegate, stage and render-settings paths, exact image path, resolution, time
limit, foreground wait, and maximum threads. This step does not render.

`render.karma.preview` accepts only a Hermes-managed ROP with the `karma_cpu_preview` role. It
requires dispatcher approval plus `policy.allow_external_process=true`, permits one frame, caps
resolution against both command policy and the conservative Apprentice ceiling of 1280×720,
enforces the configured time/output budgets, and refuses an existing image. Success requires the
expected image to exist after `husk` exits; the tool records elapsed time, byte size, delegate,
build, license, and request envelope in JSONL.

References:

- [Karma Render Settings LOP](https://www.sidefx.com/docs/houdini/nodes/lop/karmarendersettings.html)
- [USD Render ROP](https://www.sidefx.com/docs/houdini/nodes/out/usdrender.html)
- [Karma renderer](https://www.sidefx.com/products/karma/)

## Failure behavior

- Existing run-scoped LOP, MaterialX, ROP, or image names are never overwritten.
- H22 shader API parameter suffixes are not encoded in recipes; unstable generated light
  controls remain at native defaults until explicitly authored through a version-pinned tool.
- The Karma Render Settings height component is not assigned directly in H22.0.368 because it is
  locked when width drives aspect. The USD Render ROP owns the final explicit width and height.
- Missing USD prims or a missing computed material binding fail stage validation.
- Rendering never falls back to XPU, a third-party delegate, an active viewport, or hidden UI
  state.
