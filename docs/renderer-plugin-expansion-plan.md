# Optional renderer and plugin expansion plan

This lane explores third-party creative tools without weakening the repository's graph-first,
license-aware Karma baseline. Optional plugins are capabilities, not ambient dependencies: every
one must declare an exact host build, license, package hash, install root, enable switch, rollback,
node inventory, cook/render budget, and rendered proof.

## Current Octane audit — 2026-08-23

The workstation is Apple Silicon (`arm64`) on macOS 26.5. The only installed Houdini application
is 22.0.368 and its live license is Apprentice. Two relevant downloads exist:

- `Octane_2025.2.1.0_Houdini_Prime_macos.zip`, containing plugin builds for Houdini 19.5 and
  20.0/20.5 only;
- `octane_blender_addon-31.10-stable.zip`, which is a Blender addon and must never enter a Houdini
  package path.

The Houdini archive SHA-256 is
`4065003244f4b300eafa8131ca36b3b60e8b4ffa62c3052f04de4710b948d04e`. Its newest local binary is
named `Houdini_Octane_20.5.613.dylib`, so it is ABI-incompatible with Houdini 22.0.368. OTOY's
current matching release is OctaneRender 2026.4.0.0 Prime for macOS/Houdini 22.0.368. SideFX's
Apprentice restrictions independently state that Apprentice does not work with third-party
renderers. Installing either local archive would therefore be both unsupported and untestable.

No plugin files, Houdini preferences, package JSON, or app bundles were changed. The pure
`scripts/audit_octane_package.py` command records this decision without extracting or loading
vendor code.

## Octane creative horizon

Once an Indie, Education, Core, or FX license is active and the exact 2026.4/H22.0.368 archive is
available, Octane earns an experimental lane for capabilities that materially differ from Karma:

1. **Spectral material foundry.** Rebind Sprint 18 channels to Octane Universal materials and
   compare spectral absorption, scattering, dispersion, thin film, random-walk SSS, and emissive
   media against the same geometry/camera in Karma.
2. **VDB light sculptures.** Render Pyro, MPM, and reaction-diffusion-derived VDBs with independent
   absorption, scattering, emission, temperature, and velocity-driven motion blur.
3. **Massive generative populations.** Feed district lots, particles, RBD pieces, and botanical
   grammars into Octane-native instancing; preserve `P/orient/scale/v` contracts and use renderer
   instance IDs for deterministic shading variation.
4. **Vectron SDF worlds.** Author a very small approved OSL/Vectron library for recursive SDF
   sculpture, fractal architecture, morphing fields, and material/object IDs. This is development
   mode only because Octane OSL has its own supported subset.
5. **Non-physical cameras.** Explore OSL camera projections, spectral lens artifacts, panoramic
   environments, baking cameras, and deliberate optical distortion as editable recipes.
6. **Solaris renderer variants.** Prefer the Octane Solaris/Hydra route for USD-native comparison
   where it covers the scene. Keep the integrated OBJ/ROP plugin as a separate adapter. OTOY notes
   that Houdini 22 Gaussian Splat rendering is not yet supported in the current Solaris release.
7. **Critique-ready AOVs.** Standardize beauty, albedo, normals, depth, motion, IDs/Cryptomatte,
   denoised beauty, and spectral/lighting variants into the existing verification packet. Metrics
   may reject technical defects but never declare an aesthetic winner.

## Gated installation sequence

The future installation is allowed only when both license and exact-build gates pass:

1. Record live Houdini license/build, archive name, SHA-256, code signature, quarantine state,
   vendor release URL, and EULA version.
2. Extract to a versioned external root such as
   `/Applications/Houdini/sidefx_packages/Octane_2026.4.0.0_H22.0.368`; never mix vendor files into
   this repository or the Houdini app bundle.
3. Create one version-scoped `Octane.json` package with an absolute `OCTVERSION` and an explicit
   enable switch. Back up any prior file; uninstall means disabling/removing this one JSON and the
   versioned vendor directory.
4. Launch an isolated hython/Houdini preference root first. Verify plugin discovery, expected node
   types, renderer/device report, zero startup errors, and clean shutdown before touching the
   normal interactive profile.
5. Build a disposable sphere/volume/instance fixture. Render one low-sample frame at 640×360 and
   validate exit code, pixels, device, elapsed time, memory, AOVs, and provenance.
6. Only then add optional `renderer.octane.*` tools/recipes. Every skill must refuse when the exact
   plugin, compatible host build, renderer license, or project opt-in is absent.

## Other plugin priorities

| Priority | Tool | Creative value | Current recommendation |
|---|---|---|---|
| A | SideFX Labs production build | Modeling, games, terrain, VAT, photogrammetry and workflow utilities | Best first install; pin the H22 production build and fixture-test used nodes |
| A | Substance via SideFX Labs | Parametric SBSAR materials directly in COPs, usable by terrains, geometry, and materials | Strong companion to Sprint 18; keep SBSAR license and color-space provenance |
| A | MOPs open source | Fast falloffs, transforms, replication, sequencing, motion graphics | Research/install after H22 fixture check; base MOPs supports any Houdini license |
| B | MOPs Plus | Typography, cameras, dynamics, MOPsDOPs | Paid and optional; justify with a concrete motion-design sprint |
| B | Octane 2026.4 integrated/Solaris | Spectral GPU rendering, volumes, instancing, OSL/Vectron | Blocked until Houdini license upgrade and exact package acquisition |
| C | Other Hydra renderers | Renderer diversity and USD interoperability | Evaluate one at a time only after Indie/Education; never make several ambient dependencies |

SideFX Labs, Substance-in-COPs, and base MOPs expand creative construction while remaining much
closer to the graph-first source artifact than a renderer replacement. They should precede paid or
license-gated renderer proliferation.

For the active Apprentice execution path, including the live Houdini 22 node inventory, native
World Seed Atlas brief, reversible SideFX Labs integration, MOPs trial, and Sprints 19–22, see
[`apprentice-creative-expansion-plan.md`](apprentice-creative-expansion-plan.md). This document now
serves primarily as the deferred renderer-upgrade lane.

## Decision

Do not install the downloaded Octane 2025.2.1 Houdini archive into Houdini 22.0.368. The next
actionable Octane milestone requires: (a) a non-Apprentice Houdini license that permits third-party
renderers, and (b) the exact OTOY 2026.4.0.0 macOS Prime archive for Houdini 22.0.368. After both
are present, run the isolated install/probe sequence above before any creative scene work.

## Primary sources

- SideFX, Apprentice restrictions: https://www.sidefx.com/faq/question/apprentice-restrictions/
- OTOY, OctaneRender 2026.4 for Houdini: https://render.otoy.com/forum/viewtopic.php?t=85766
- OTOY, OctaneRender for Solaris 2026.4: https://render.otoy.com/forum/viewtopic.php?p=444003
- OTOY, Houdini volumes: https://docs.otoy.com/houdini/Volumes1.html
- OTOY, Houdini instances: https://docs.otoy.com/houdini/Instances.html
- OTOY, Vectron: https://docs.otoy.com/osl/vectron/
- SideFX Labs installation: https://github.com/sideeffects/SideFXLabs/blob/Development/docs/installation.md
- Adobe, Substance for Houdini: https://experienceleague.adobe.com/en/docs/substance-3d/ecosystem/3d-applications/houdini
- MOPs documentation: https://github.com/toadstorm/MOPS/wiki
