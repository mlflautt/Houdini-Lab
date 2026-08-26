# G001 acceptance fixtures

The G001-B fixtures are rebuilt by
`hermes_houdini.acceptance.fixtures.build_acceptance_fixtures`. The caller must provide an unused
absolute artifact root. The builder creates native, graph-readable SOP, Solver SOP, ROP Geometry
TOP, explicit-camera viewport, Solaris, and Karma CPU contracts, then saves one non-commercial
`.hipnc` scene under that root.

No generated `.hipnc`, geometry cache, viewport image, or render is committed. Graph construction
does not cook geometry or render pixels. The read-only, graph-edit, single-frame, frame-range,
PDG-child, simulation, viewport, and Karma adapters remain separate calls.

Default ceilings are 10,000 points, 8 frames, 256 MiB observed memory, 256 MiB artifacts,
640x360 pixels, 16 Karma samples, one PDG work item, and 120 seconds. PDG child execution requires
explicit external-process authorization. Simulation and Karma refuse missing explicit
authorization. In bare Hython, viewport evidence is truthfully `pending` because no GUI viewport
exists.
