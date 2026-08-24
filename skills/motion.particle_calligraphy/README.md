# Particle calligraphy

`motion.particle_calligraphy@1.0.0` builds three native Houdini 22 Particle Trail branches:
arc, fan, and orbit. Every branch stays editable from emitter through Particle SOP, attribute
normalization, Time Blend, Particle Trail, a documented half-frame compatibility boundary, and
PolyWire. A human Switch selects a working view while the comparison output preserves and labels
all three candidates with their IDs and seeds.

The default fixture is silent and deterministic: seed `5201`, frames `1-48`, 48 births per
second, twelve-frame trails, eight trail substeps, and no authored winner. Optional audio response
accepts only a validated `hermes.audio_envelope.v1` JSON file relative to an explicit project root;
it checkpoints before keyframing native Particle wind parameters and never decodes audio itself.

Verification is layered. The skill first validates every frame and graph/attribute/resource
contract. With an explicit viewer, viewport, and camera it captures one Apprentice-safe PNG, runs
dependency-free mechanical image checks, and creates a hashed critique packet containing the image,
graph, validation, and relevant source. The packet is ready for a separately approved local or
external multimodal critic, but it performs no inference and carries no decision authority.

Known Houdini 22.0.368 compatibility: the legacy Particle SOP retains an emitter primitive and
stores age/lifespan in a vector2 `life` attribute. Native Add and Attribute Create/Delete SOPs
normalize those inputs. Particle Trail produces valid samples at intervening half-frames, so a
named Time Shift evaluates `$FF - 0.5` with integer rounding disabled. Both workarounds are asserted
by the validator and remain visible to an artist.
