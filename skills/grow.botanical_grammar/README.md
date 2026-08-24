# Native L-System Botanical Grammar

`grow.botanical_grammar@1.0.0` instantiates `sop.lsystem_botanical@1.0.0` as three explicit native
SOP branches: a 3D canopy, a planar fern, and a radial coral. Each L-System skeleton retains the
documented `width`, `arc`, `gen`, and `up` attributes, then feeds an editable PolyWire. A human
Switch exposes one working result while a translated Merge preserves all three for comparison.

Safe mode does not accept arbitrary grammar text or rule files. Premises and productions are
versioned in the recipe and verified before cooking; public controls are seed, one-to-six
generations, wire radius, and the human preview input. Per-candidate random-length variation is
deterministic from the recorded seed, and manifests retain empty human-rating slots with no winner.

The six-generation ceiling is deliberately stricter than the roadmap's absolute eight-generation
boundary. Live Houdini 22.0.368 measurements show the combined three-candidate PolyWire proxy stays
comfortably below the 250,000 point/primitive budget at six; the five-way coral grammar grows too
quickly to make eight a responsible default capability.

Primary references are SideFX's [L-System SOP](https://www.sidefx.com/docs/houdini/nodes/sop/lsystem),
[L-Systems Node lesson](https://www.sidefx.com/tutorials/l-systems-node/?collection=63), and
[PolyWire SOP](https://www.sidefx.com/docs/houdini/nodes/sop/polywire.html) documentation.
