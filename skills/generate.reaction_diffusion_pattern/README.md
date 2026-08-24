# Native Copernicus Reaction-Diffusion

`generate.reaction_diffusion_pattern@1.0.0` creates an explicit Float32 CopNet, then instantiates
three native Gray–Scott blocks sharing one seeded activation mask. Small Waves, Large Waves, and
Spots remain connected in that exact order to both a human Switch and a Contact Sheet COP. No
candidate is ranked or chosen as a winner.

The recipe stores each preset's `kill`, `feed`, raw, and diffusion coefficients explicitly. The
native Preset menu runs a Python callback in Houdini's UI; setting only its token through HOM does
not apply those coefficients and can silently produce duplicate candidates. Validation therefore
checks both coefficients and unique Float32 buffer hashes.

The default fixture runs in deterministic non-simulation mode with `8 × 6 = 48` integration steps
per candidate at 256×256. Live Simulation, frame caching, and compiled COP cooks are disabled. A
numeric validation tool cooks each mono output, checks Float32 resolution, finite values, dynamic
range, standard deviation, Houdini messages, memory, and elapsed time, then records the evidence as
JSON.

Native Mono to RGB nodes provide cyan, amber, and lime presentation ramps while leaving the mono
patterns available for later masks, displacement, scattering, or MaterialX. Two managed ROP Image
nodes explicitly export a 768×256 contact sheet and the selected 256×256 image. They render in the
foreground, verify the PNG header, and refuse existing files.

Primary references are SideFX's [Reaction-Diffusion solver](https://www.sidefx.com/docs/houdini/copernicus/reaction_diffusion.html),
[Block Begin](https://www.sidefx.com/docs/houdini/nodes/cop/reactiondiffusion_block_begin.html),
and [Block End](https://www.sidefx.com/docs/houdini/nodes/cop/reactiondiffusion_block_end.html)
documentation.
