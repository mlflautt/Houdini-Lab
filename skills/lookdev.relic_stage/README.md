# `lookdev.relic_stage`

Builds a readable Solaris stage around one explicit SOP output. Three native MaterialX
candidate subnets and three Assign Material branches remain editable behind a Switch;
candidate selection is a human control and never an automatic ranking.

Version 1.1 exposes bounded dome intensity/exposure and camera transform/focal-length controls as
ordinary recipe inputs. This lets an audition frame planar comparison work explicitly without
depending on viewport lighting or a manually positioned camera.

Stage composition and rendering are separate resource decisions. The USD validation step
composes one bounded LOP stage. The optional preview then launches one approved external
`husk` process through a Hermes-managed USD Render ROP using Karma CPU, at or below the
conservative Apprentice limit of 1280×720. Existing images are never overwritten.

The skill emits replay logs, a graph SVG, a provenance-rich lookdev manifest, an optional
PNG preview, and an incremented `.hipnc` snapshot.
