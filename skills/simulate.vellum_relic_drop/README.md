# `simulate.vellum_relic_drop@1.0.0`

Builds the first bounded simulation workflow in the Houdini Lab curriculum. The graph uses only
native SOPs: a closed polygon source receives cloth and pressure constraints, falls under gravity,
collides with a closed floor box, passes through a configured File Cache boundary, and remains
editable beside its rest state.

The skill cooks an explicit inclusive frame range (maximum 48 frames), records metrics for every
frame, restores the artist's original timeline frame, validates the static contracts, captures a
selection-independent graph artifact, and saves an incremented `.hipnc` snapshot. It configures a
new versioned `.bgeo.sc` cache path but deliberately does not press **Save to Disk**; cache writing
is a separate operation that needs its own output and overwrite decision.

The final comparison output is `OUT_<RUN_ID>_COMPARE`. Other continuation points are named
`OUT_<RUN_ID>_REST`, `OUT_<RUN_ID>_CONSTRAINTS`, `OUT_<RUN_ID>_COLLIDER`,
`OUT_<RUN_ID>_SIM_RAW`, and `OUT_<RUN_ID>_CACHE`.
