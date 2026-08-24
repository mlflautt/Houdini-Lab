# Kinetic reliquary

Sprint 22 compares one native packed-fragment motion branch with three MOPs 1.12 falloff branches:
plain, animated noise, and a moving spherical influence. All four expose `P`, `orient`, `scale`,
`v`, `seed`, and `variant_id`; the native branch is always Switch input zero.

Set `mops_available=false` unless an exact isolated MOPs capability probe has passed. That mode
builds `OPTIONAL_MOPS_UNAVAILABLE` and never instantiates an unknown HDA.
