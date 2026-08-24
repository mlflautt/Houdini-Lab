# Procedural Material Foundry

`lookdev.procedural_material_foundry@1.0.0` is Sprint 18's graph-first bridge from reusable
Copernicus patterns to editable USD/MaterialX look development. It preserves three candidates—
Verdigris, Emberglaze, and Moonlichen—without selecting a winner.

Each candidate exposes named `base_color`, `roughness`, `height`, and `normal` Null COP contracts.
The base color carries scene-linear Rec.709 intent; the other maps are raw data. A native USD
Material COP consumes all four channels, and Houdini 22's Texture Material Library LOP publishes
the material into Solaris. Three equal polygon spheres give human reviewers a comparable Karma
gallery instead of an automatically ranked result.

Default pattern/channel resolution is 512 square with a 1024 square ceiling. The optional Karma
proof is one 960 by 540 frame and remains separately approved external work. Every mutation is
checkpointed, every artifact is non-overwriting, and the final scene is `.hipnc`.

Primary references: SideFX's [working with COPs](https://www.sidefx.com/docs/houdini/copernicus/working_with_cops.html),
[Houdini 22 Copernicus changes](https://www.sidefx.com/docs/houdini/news/22/copernicus.html), and
[ROP Image](https://www.sidefx.com/docs/houdini/nodes/cop/rop_image.html).
