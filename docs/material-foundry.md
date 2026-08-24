# Sprint 18 — procedural material foundry

Sprint 18 turns reusable Copernicus patterns into a small, editable material system rather than a
single baked texture. The public capability is
`lookdev.procedural_material_foundry@1.0.0`; its graph sources are:

- `cop.reaction_diffusion_pattern@1.0.0` for three deterministic mono identities;
- `cop.procedural_material_foundry@1.0.0` for named PBR channels and USD Material COPs;
- `sop.material_swatch_gallery@1.0.0` for equal comparison geometry;
- `lop.procedural_material_foundry_stage@1.0.0` for USD publication, binding, lighting, camera,
  and Karma settings.

The system is intentionally not tied to reaction diffusion. Any finite mono COP with the declared
resolution can replace a pattern reference: scanned masks, cellular noise, heightfield masks,
growth fields, or future PDG-generated images all enter at the same three external recipe paths.
The downstream channel, MaterialX, USD, and proof contracts remain unchanged.

## Graph and channel contract

The fixed comparison order is Verdigris, Emberglaze, Moonlichen. Each branch retains these named
outputs:

| Channel | COP contract | Components | Intent | Use |
|---|---|---:|---|---|
| `base_color` | `OUT_<RUN>_<ID>_BASE_COLOR` | 3 | scene-linear Rec.709 | Material color |
| `roughness` | `OUT_<RUN>_<ID>_ROUGHNESS` | 1 | raw data | Specular roughness |
| `height` | `OUT_<RUN>_<ID>_HEIGHT` | 1 | raw data | Bump/displacement source |
| `normal` | `OUT_<RUN>_<ID>_NORMAL` | 3 | raw offset 0–1 | Tangent-space normal |

Native `monotorgb`, `remap`, `heighttonormal`, `null`, and `usdmaterial` COPs perform all image
work. The USD Material COP receives the four contracts on explicit sockets. No Python SOP, image
array loop, generated VEX, selection state, or pane path computes the material.

Houdini 22's `texturemateriallibrary` LOP consumes the absolute USD Material COP paths. One
three-entry Assign Material LOP binds `/World/Swatches/Verdigris`, `Emberglaze`, and `Moonlichen`
to three material paths simultaneously. This differs deliberately from Sprint 8's human Switch:
Sprint 18's output is the comparison itself, not one chosen branch.

## Budgets and safety

- Default channel resolution: 512×512; accepted values 64, 128, 256, 512, 1024.
- Maximum observed image-buffer budget: 1 GiB.
- Reaction-diffusion seed and 36 integration steps are explicit and deterministic.
- Default proof: one 960×540 Karma CPU frame; hard Apprentice ceiling 1280×720.
- Rendering remains a separately approved external process.
- Every mutation checkpoints first; images and JSON evidence refuse overwrite.
- The final scene is incremented `.hipnc`; candidate rating slots remain empty.

## Verification ladder

`cop.material_foundry.validate` cooks all twelve named channel contracts and checks exact roles,
components, resolution, Float32 storage, finite pixels, dynamic range, variance, 0–1 raw-data
ranges, distinct base-color hashes, elapsed time, and memory. It also proves each USD Material COP
is wired to base color, roughness, height, and normal rather than merely trusting metadata.

`solaris.material_foundry.validate` composes the bounded stage once, checks all three swatch and
material prims, computes each bound material through `UsdShade.MaterialBindingAPI`, and requires a
connected MaterialX output on every material. The one-frame proof then passes through the existing
local deterministic image gate and hashed critique-packet builder. These mechanisms may reject a
broken result or flag framing; they do not rank visual taste.

## Live Houdini 22.0.368 evidence

Acceptance used 256×256 channels and a 768×432 Apprentice Karma proof. All twelve buffers were
finite and non-flat. Base colors had three components; roughness and height had one; normals had
three. All scalar/vector data remained inside 0–1, all three MaterialX outputs connected, and all
three USD bindings resolved.

The first render is retained as diagnostic evidence because the deterministic gate found both
outer swatches touching the border. A second non-overwriting render moved the explicit camera from
10.5 to 22.5 units, after which all three panels were present with no crop flag. The accepted image
is `.hermes/sprint18-live/observations/sprint18_refined_karma_cpu.png`; its report is
`.hermes/sprint18-live/manifests/sprint18_refined_visual_verification.json`.

## Failure modes

- Reordered or renamed candidate IDs fail before mutation.
- Missing/stale channel roles, components, hashes, connections, or material outputs fail before
  render.
- Existing artifact paths are never replaced.
- Full geometry displacement is not enabled in this proxy gallery; height and normal both remain
  available for an artist to tune. The proof emphasizes channel-to-shader correctness.
- Houdini 22.0.368 may print harmless `fractalnoise` handle-binding warnings while loading the
  operator definition. Cooked channel contracts themselves must still report no node warnings or
  errors.

## Sources

- SideFX, [Working with COPs](https://www.sidefx.com/docs/houdini/copernicus/working_with_cops.html)
  — `op:` COP material inputs and the Texture Material Library workflow.
- SideFX, [Houdini 22 Copernicus changes](https://www.sidefx.com/docs/houdini/news/22/copernicus.html)
  — improved material authoring and Preview Material behavior.
- SideFX, [Houdini 22 Karma changes](https://www.sidefx.com/docs/houdini/news/22/karma.html)
  — MaterialX and Texture Material Library support.
- SideFX, [ROP Image COP](https://www.sidefx.com/docs/houdini/nodes/cop/rop_image.html) — explicit
  raw/AOV color-conversion semantics for exported data channels.
