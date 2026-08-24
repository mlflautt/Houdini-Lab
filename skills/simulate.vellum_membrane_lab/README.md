# `simulate.vellum_membrane_lab@1.0.0`

Builds three native pinned Grid membranes—silk, rubber, and reinforced—and cooks every requested
frame through independent Vellum Solvers against one explicit sphere-plus-floor collider. The
reinforced branch layers Surface Struts over Cloth and Pin constraints; ordinary Struts are not
used because live Houdini 22.0.368 probing showed they create no reinforcement on this open sheet.

The default 25×25 membrane pins one 25-point edge. Validation refuses the historical failure where
the Pin node's secondary `pingroup` field zeroes mass on the whole sheet: the registered graph uses
the main point Group field and verifies 25 zero-mass anchors plus 600 dynamic points. Material
profiles, seed-derived native Mountain perturbations, frame range, solver budgets, comparison order,
cache paths, and empty human ratings are all recorded.

File Cache nodes pass through live simulation and keep Load from Disk off. No cache sequence is
written. Optional visual capture requires explicit viewer, viewport, and camera identifiers, then
runs deterministic image diagnostics and packages—but does not execute—a multimodal critique.
