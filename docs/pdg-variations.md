# Local PDG variation system

Sprint 6 adds a bounded local variation lane for promoted Houdini assets. It uses native TOP
nodes for work-item generation and geometry output; no Python Processor or Python Script TOP is
created.

```text
                         +-> LOCAL_BOUNDED (one process slot)
                         |
TOP_WEDGE_VARIANTS -> CACHE_VARIANT_GEOMETRY -> WAIT_ALL_VARIANTS -> OUT_VARIATIONS
       parameter push       ROP Geometry TOP
```

This follows SideFX's documented model: the Wedge TOP creates one work item per variation and can
push work-item values into target parameters without editing the HIP; the ROP Geometry Output TOP
cooks SOP geometry for those incoming items. `hou.TopNode.generateStaticWorkItems` is used for the
non-executing manifest pass, and `cookWorkItems` is used only after the bounded local-job approval.

References: [Wedge TOP](https://www.sidefx.com/docs/houdini/nodes/top/wedge),
[ROP Geometry Output TOP](https://www.sidefx.com/docs/houdini/nodes/top/ropgeometry.html),
[hou.TopNode](https://www.sidefx.com/docs/houdini/hom/hou/TopNode.html), and
[Local Scheduler](https://www.sidefx.com/docs/houdini/nodes/top/localscheduler.html).

## Tools

`pdg.variation.build` checkpoints the scene and creates a new `/tasks/HERMES_PDG_*` network. The
source must be an externally published SOP HDA with these controls: `seed`, `base_radius`,
`noise_amplitude`, `iterations`, `detail_level`, `preview_candidate`, and `output_mode`.

The Wedge varies seed, base radius, and noise amplitude along deterministic linear ranges. It also
pushes fixed iteration, detail, candidate, and selected-output values. The source parameters are
checked before and after the run and must remain identical.

`pdg.variation.generate` generates static Wedge items only. It writes an immutable plan manifest
with the resolved attributes, geometry destinations, lineage, empty rating slots, and an explicitly
null human winner. It starts no scheduler jobs.

`pdg.variation.cook` requires both a single-use medium-risk approval and
`policy.allow_external_process=true`. Before starting, it validates:

- work-item count;
- total declared duration;
- point and primitive limits per item;
- worker memory per item;
- total output bytes;
- a matching immutable plan manifest;
- new `.hipnc`, result, and `.bgeo.sc` paths.

The generated Local Scheduler uses one slot, zero retries, a 30-second default item timeout, a
2 GiB worker ceiling, and a task-specific temporary directory. The 2 GiB limit accounts for the
Houdini worker process itself; geometry point/primitive and output-byte budgets remain separate and
much smaller. A local `HOUDINI_OTLSCAN_PATH` override exposes only the source `.hdanc` directory to
the jobs and does not modify global Houdini configuration.

Successful geometry is re-opened read-only for point/primitive/memory/file-size and finite-bounds
validation. Partial files are retained and reported if a worker fails; the tool never silently
deletes evidence or overwrites a prior run.

`pdg.variation.build_gallery` checkpoints again and creates an editable native SOP grid. Each File,
Transform, Font label, and label-Transform SOP retains the variation id, seed, and empty human-rating
record as user data. All form branches are connected before the label branches so the Merge SOP has
an exact `2 × variation count` input contract. A named `OUT_GALLERY` and explicit camera support data
and viewport validation. The resulting labeled 1280×720 viewport capture is the human-facing contact
sheet; it is generated only when explicit GUI viewer handles are supplied.

## Skill boundary

`generate.fractal_relic_variations@1.0.0` limits an executable local run to 2–16 work items even
though the pure plan schema can describe up to 100. Larger studies require a new explicit resource
decision. The skill records comparable outputs and human rating slots; it never calculates a score,
declares a winner, or mutates geometry based on ratings.

All artifacts remain Houdini Apprentice/non-commercial. `.bgeo.sc` caches, `.hipnc` snapshots, the
source `.hdanc`, plan/result manifests, TOP/SOP graph SVGs, and the optional contact sheet retain a
single provenance chain.
