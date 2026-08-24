# Native Copernicus reaction diffusion

Sprint 10 turns Houdini 22's Reaction Diffusion COP into a bounded, graph-first generative-mask
capability. `cop.reaction_diffusion_pattern@1.0.0` is the editable graph and
`generate.reaction_diffusion_pattern@1.0.0` is the orchestration skill. Native COPs perform every
pixel operation; HOM only creates, connects, validates, observes, and saves the graph.

## Graph and artistic controls

One seeded Fractal Noise and Remap define a shared activation mask. Three explicit native block
pairs then produce candidates in this stable order:

1. `smallwaves` — Small Waves, cyan presentation ramp.
2. `bigwaves` — Large Waves, amber presentation ramp.
3. `spots` — Spots, lime presentation ramp.

Each Reaction Diffusion Block Begin points by absolute path to its paired Block End at the same
CopNet level. The mono outputs remain available as masks; Mono to RGB nodes affect presentation
only. A human-controlled Switch selects the working preview, while a native Contact Sheet preserves
all three alternatives. Stable Hermes IDs, roles, lineage, seed, and empty rating slots are stored
in the manifest. No score or winner is inferred.

The Preset parameter is callback-driven. A HOM `parm.set("smallwaves")` changes the visible token
but does not execute `hou.phm().setPreset_GS(kwargs)`. The recipe therefore stores the callback's
Houdini 22.0.368 coefficients explicitly:

| Candidate | Normalized kill | Normalized feed | Raw kill | Raw feed |
|---|---:|---:|---:|---:|
| Small Waves | 0.3865 | 0.0899 | 0.051 | 0.018 |
| Large Waves | 0.0000 | 0.0444 | 0.045 | 0.014 |
| Spots | 0.8045 | 0.2222 | 0.062 | 0.030 |

All three use Gray–Scott, diffusion A/B `1.0/0.5`, normalization, and a clamped 0–1 output.

## Resource and safety contract

- Tested build: Houdini 22.0.368 Apprentice; Copernicus nodes require Houdini 21 or newer.
- Resolution choices: 64, 128, 256, or 512 square; default 256. At 512, the Contact Sheet scales
  to 768×256 so evidence remains inside the conservative Apprentice ceiling.
- Deterministic fixture: Simulate, Live Simulation, cache, and compiled COP cook are disabled.
- Integration work: `Iterations × Iterations per Step ≤ 48`; default `8 × 6`.
- Validation reads native Float32 image layers and refuses wrong resolution/storage, non-finite
  values, low dynamic range, low standard deviation, node messages, stale preset coefficients,
  duplicate buffer hashes, memory excess, or timeout.
- `cop.image.export` accepts only tagged managed ROP Image nodes, renders the current frame in the
  foreground, writes PNG only, refuses overwrite, verifies the PNG header/resolution, restores the
  timeline, and appends provenance.
- The skill creates an incremented `.hipnc` snapshot after graph and image evidence complete.

SideFX notes that reaction diffusion is resolution-sensitive and that doubling resolution can
require roughly four times as many substeps with a quarter time scale. This skill does not silently
scale those costs; higher-quality or live-simulation studies require a new explicit contract.

## Verified Sprint 10 evidence

The final acceptance fixture used seed 3109, candidate Switch input 1, 256×256 candidates, and 48
integration steps in Houdini 22.0.368 Apprentice:

- 17 native Copernicus nodes and 20 wires; no Python COP or Python image computation.
- Three distinct mono SHA-256 buffer hashes, with dynamic ranges `1.0`, `1.0`, and `0.972764`.
- Standard deviations `0.156289`, `0.204247`, and `0.099825`; zero non-finite values and no node
  errors or warnings.
- Validation observed 3,145,728 bytes of Float32 buffers in 0.686 seconds.
- Native 768×256 Contact Sheet PNG: 139,056 bytes, foreground export in 0.195 seconds.
- Selected 256×256 PNG: 49,303 bytes, foreground export in 0.016 seconds.
- Versioned non-commercial scene, graph SVG, graph manifest, image-validation JSON, and JSONL
  command/export provenance accompany the images under `.hermes/sprint10-live-2/`.

The first live acceptance run is intentionally preserved under `.hermes/sprint10-live/`. It proved
that preset tokens alone produced three identical mono buffers. That evidence drove the explicit
coefficient contract and duplicate-buffer refusal now covered by both pure and Hython tests.

## References

- SideFX: [Reaction-diffusion solver](https://www.sidefx.com/docs/houdini/copernicus/reaction_diffusion.html)
- SideFX: [Reaction Diffusion Block Begin](https://www.sidefx.com/docs/houdini/nodes/cop/reactiondiffusion_block_begin.html)
- SideFX: [Reaction Diffusion Block End](https://www.sidefx.com/docs/houdini/nodes/cop/reactiondiffusion_block_end.html)

The weighted SOP, volume, and artistic-use tutorials collected in
[`docs/skill-curriculum.md`](skill-curriculum.md) remain study references for later recipes, not
opaque code copied into this capability.
