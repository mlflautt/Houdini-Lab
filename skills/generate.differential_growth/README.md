# Native differential growth

`generate.differential_growth@1.0.0` builds a readable SOP network around a native Solver feedback
loop. Point Relax supplies local separation, Attribute Blur on `P` supplies the opposing smoothing
force, and Resample controls edge spacing. HOM only constructs and tags those nodes; Houdini SOPs
perform the geometry work.

The skill preserves circle, ellipse, and open-spiral sources behind an explicit Switch. The default
ellipse is a useful structural fixture, not a selected winner. Every candidate keeps the same seed,
lineage, and empty human-rating fields so comparisons stay human-directed.

Default execution cooks frames 1–24 in memory, logs each frame's geometry metrics, captures both the
outer recipe and inner Solver graph, writes a manifest, and saves an incremented `.hipnc` snapshot.
It does not write a simulation cache or start an external renderer. Pass an explicit GUI viewer,
viewport, and camera together for a 1280×720 final-frame viewport capture; a downstream
`lookdev.relic_stage` run can supply a separately approved Karma CPU proof.

Primary study source: SideFX's
[Complex Growth in 2 Nodes](https://www.sidefx.com/tutorials/complex-growth-in-2-nodes/), with the
native [Attribute Blur](https://www.sidefx.com/docs/houdini/nodes/sop/attribblur.html),
[Resample](https://www.sidefx.com/docs/houdini/nodes/sop/resample.html), and
[PolyWire](https://www.sidefx.com/docs/houdini/nodes/sop/polywire.html) documentation.
