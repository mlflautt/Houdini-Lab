# generate.fractal_relic_variations

`generate.fractal_relic_variations@1.0.0` turns a published
`hermes::fractal_relic::2.0` instance into a bounded local PDG study.

The editable TOP graph is native and explicit:

```text
TOP_WEDGE_VARIANTS -> CACHE_VARIANT_GEOMETRY -> WAIT_ALL_VARIANTS -> OUT_VARIATIONS
        LOCAL_BOUNDED (one slot, per-item timeout and memory ceiling)
```

The Wedge TOP pushes seed, form, iteration, detail, candidate, and output-mode overrides into
the ROP Geometry work items. Houdini writes one non-commercial `.bgeo.sc` per item without
changing the source asset's parameter values. A second native SOP graph loads the successful
outputs into an editable, seed-labeled comparison grid with an explicit camera.

The immutable plan/result manifests keep lineage and empty human rating slots. The skill never
ranks, deletes, or silently chooses a winner. Local hython jobs require an exact medium-risk
approval and `policy.allow_external_process=true`; existing geometry, manifests, scenes,
networks, and galleries are refused rather than overwritten.
