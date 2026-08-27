# G003 Owner Decision — Motion Language

Select one direction for the live Living Biome composition. These options are not ranked; each is
already registered, tested on Houdini 22.0.368, and preserves three candidates.

| Choice | Exact capability | Native shape and contract | Runtime boundary |
|---|---|---|---|
| Particle trails | `motion.particle_calligraphy@1.0.0` | Arc, fan, and orbit Particle Trail/PolyWire branches; consume the three explicit tube outputs, not `human_selected_contract` | Medium risk; up to 48 frames and 100,000 trail points; silent fixture unless a separate baked envelope is supplied |
| Organic growth | `generate.differential_growth@1.0.0` | Three editable curve sources through native Solver growth; consume explicit grown PolyWire outputs | Medium risk; default 24-frame growth solve; 50,000-point class ceiling retained from the registered capability |
| Kinetic instances | `motion.kinetic_reliquary@1.1.0` | Native packed-copy motion with optional MOPs branches; G003 must use the native branch and unavailable markers unless MOPs receives separate approval | Capability class is external; default 24 frames and 8–64 copies; optional render and MOPs remain off |

The decision selects a vocabulary for implementation, not a winning rendered result. Candidate
ratings and biome continuation remain unresolved after this choice.

Reply with one exact sentence:

```text
Use motion.particle_calligraphy@1.0.0 for G003.
```

or

```text
Use generate.differential_growth@1.0.0 for G003.
```

or

```text
Use motion.kinetic_reliquary@1.1.0 native-only for G003.
```

The orchestrator must then amend `CYCLE_MANIFEST.md` with the selected ID/version, exact three
candidate outputs, final stage ceilings, and the verbatim decision before launch acceptance.
