# Houdini Apprentice creative expansion and plugin plan

This plan deliberately treats Houdini Apprentice as a deep non-commercial creative system, not
as a waiting room for a paid license. The first goal is to compose the powerful native systems
already verified on this workstation. Plugins enter only when they add a clear graph-editable
capability and can be enabled, tested, and removed without contaminating artist preferences or
project files.

## What Apprentice can use

The current license boundary is narrow but important:

- Houdini's native modeling, SOP, VEX, simulation, Copernicus, KineFX/APEX, Solaris, USD, PDG,
  Karma CPU, and Mantra systems remain available for personal non-commercial work.
- Scenes and digital assets remain non-commercial (`.hipnc` and `.hdanc`), renders are restricted,
  and this repository conservatively caps them at 1280x720.
- Houdini Engine and third-party renderers are not available under Apprentice.
- Apprentice does **not** imply a blanket ban on tool packages. HDAs, Python tools, viewer states,
  shelf tools, VEX libraries, and compatible native operators may be usable when their own license,
  architecture, and Houdini-build requirements allow it.

SideFX distributes SideFX Labs as a separately installable package, and its repository describes
the package as a free, open-source collection of HDAs, Python modules, UI extensions, VEX, and other
tools. MOPs documents Houdini 18 or later and "any license type" for its open-source base package.
Those two are the best first candidates. They do not alter the prohibition on third-party renderers.

Primary references:

- [SideFX Apprentice restrictions](https://www.sidefx.com/faq/question/apprentice-restrictions/)
- [SideFX Labs installation](https://www.sidefx.com/docs/houdini/licensing/install_labs_packages.html)
- [SideFX Labs source and license](https://github.com/sideeffects/SideFXLabs)
- [MOPs requirements](https://github.com/toadstorm/MOPS/wiki)
- [Houdini package files](https://www.sidefx.com/docs/houdini/ref/plugins.html)

## Live capability inventory — 2026-08-23/24

A read-only Hython probe against Houdini 22.0.368 reported
`licenseCategoryType.Apprentice` and confirmed native operators in the following families:

| Family | Live evidence | Existing Hermes work |
|---|---|---|
| Generative geometry | Copy/instance, curves, volumes, HeightFields, VEX, For-Each | Fractal relic, differential growth, botanical grammar, procedural district |
| Soft matter | Vellum solvers and constraints, grains, tissue/muscle nodes | Relic drop and membrane lab |
| Matter and destruction | MPM source/solver/surface, Bullet and RBD fracture/constraints | MPM matter sculpture and art-directed destruction |
| Fields and images | Copernicus reaction, Pyro, terrain, and USD material nodes | Reaction diffusion and procedural material foundry |
| Motion and characters | Particle workflows plus extensive KineFX/APEX rig, clip, retime, IK, and scene nodes | Particle calligraphy; character work remains open territory |
| Worlds and rendering | USD/Solaris, Karma, MaterialX, instancing, Physical Sky, Cryptomatte | Relic stage, material stage, verification renders |
| Variation systems | TOP/PDG Wedge, cache, USD and Karma work items | Deterministic variation galleries |

The pre-install baseline contained only three `labs::`-namespaced ZibraVDB definitions. After
explicit approval, SideFX Labs 22.0.368 was checksum-pinned and installed in Houdini's user package
scope. Enabled startup exposes 450 matching types; a verified
`HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json` launch returns to the three-node baseline. Only three
exact Labs node types are currently certified. MOPs 1.12 is now pinned project-locally and loaded
only in isolated processes; no global Houdini preference was changed.

## Implemented native baseline: World Seed Atlas

Before introducing a dependency, the roadmap composed one ambitious native project from capabilities
already available. **World Seed Atlas** is a deterministic family of miniature alien biomes:

1. Copernicus terrain layers generate strata, terraces, erosion, flow, and masks.
2. The material foundry derives coherent rock, soil, emissive growth, roughness, normal, and height
   channels from the same seed and terrain fields.
3. Botanical grammar and district systems reinterpret masks as vegetation, crystalline settlement,
   paths, and landmarks.
4. Optional bounded Vellum, MPM, or Pyro accents add cloth membranes, deposited matter, mist, or
   atmospheric motion without making simulation mandatory.
5. Solaris assembles three equal-status seed variants and Karma renders a comparison atlas. Data
   gates reject broken outputs; `human_rating` remains empty and no variant is named the winner.

This project exercises Houdini 22's native terrain COP workflow, which SideFX documents as supporting
noise, strata, terraces, erosion, slump, feature masks, texture ramps, and geometry conversion. It
also creates a strong baseline against which any plugin must demonstrate genuine value rather than
novelty. See [Houdini 22 terrain additions](https://www.sidefx.com/docs/houdini/news/22/model.html)
and [heightfield workflow](https://www.sidefx.com/docs/houdini/heightfields/index.html).

### World Seed Atlas acceptance

- Three fixed seed IDs and complete provenance; no automatic ranking.
- Named contracts for terrain, biome masks, scatter points, hero forms, material channels, and USD.
- Bounded default: 512x512 terrain/material fields, at most 150,000 display points, at most 48
  simulated frames, and a 768x432 comparison proof.
- Structural validation of every graph plus finite/range checks for fields and attributes.
- Render proof with panel-presence, crop, blank-frame, and temporal-difference checks.
- A `.hipnc` fixture remains understandable and editable when every optional plugin is disabled.

## Plugin integration architecture

Plugins remain adapters around the native graph, never hidden foundations.

```text
native recipe and contracts
          |
          +-- plugin disabled -> native editable output and Karma proof
          |
          `-- plugin enabled  -> optional enhancement branch -> same output contract
```

Every installed package receives a registry record containing:

- plugin ID, vendor, source URL, SPDX/vendor license, package version, archive hash;
- supported Houdini range, operating system, architecture, Python/Qt/HDK ABI needs;
- installation root, package JSON path, enabled state, and one-command rollback;
- declared node types and contexts, external executables/services, network behavior, and telemetry;
- fixture scenes, expected nodes, cook/render budget, observed warnings, and proof artifacts;
- Apprentice verdict: `allowed`, `blocked`, or `conditional`, with an explicit reason.

Use versioned external tool roots and one package JSON per plugin. Never edit `houdini.env`, mix
files into the Houdini application bundle, or silently update a pinned dependency. The package
starts disabled, is tested under an isolated preference root, and enters the normal profile only
after the fixture passes. Houdini's package system provides explicit `enable`, version conditions,
skip lists, and package diagnostics for this purpose.

## Plugin stage A — SideFX Labs

SideFX Labs is the first integration because it is SideFX-maintained, open source, graph-visible,
and broad enough to improve several existing projects. Use the SideFX Installer's Labs/Packages
channel for the production-compatible Houdini 22 package offered to this 22.0.368 installation;
record the exact installed package rather than assuming a GitHub daily tag is compatible.

### Installation gate

1. Record current package directories and Houdini startup logs.
2. Ask for explicit approval immediately before the external package installation.
3. Install into a versioned SideFX package root, not the repository or app bundle.
4. Copy or generate a disabled, version-scoped package definition for isolated validation.
5. Run Hython startup with package verbosity; inventory all added node types and binary libraries.
6. Scan node definitions for missing dependencies and cook three disposable fixtures.
7. Enable it for normal Houdini only after clean startup, clean shutdown, and visual proof.

### First Labs studies

- **Terrain cartography:** add only the Labs terrain/UV/baking tools that materially improve the
  World Seed Atlas, and retain the native terrain as a Switch alternative.
- **Artifact fabrication:** test mesh cleanup, UV, curvature, maps-baking, and detail-transfer tools
  on the fractal relic and RBD interior surfaces.
- **Motion/export study:** test one graph-visible instancing or animation utility, but keep export
  optional because Apprentice output licensing remains non-commercial.

Acceptance requires three fixture graphs, deterministic geometry statistics, a 768x432 gallery,
zero startup errors, and a verified disable/rollback launch. We do not certify the entire Labs
catalog merely because three tools pass.

## Plugin stage B — open-source MOPs

MOPs follows Labs because it targets a specific creative gap: readable motion-graphics falloffs,
replication, sequencing, and transform composition. Pin a tagged release and audit its package,
license, Python, and HDA definitions before loading it into an isolated profile.

The fixture is a **kinetic reliquary**: one native point/transform source drives repeated relic
fragments through three preserved falloff variants. MOPs and native branches must expose equivalent
`P`, `orient`, `scale`, `v`, seed, and variant-ID contracts. A short flipbook validates motion,
collisions/cropping, temporal change, and deterministic replay. MOPs may make authoring clearer; it
must not make the asset unreadable when absent.

## Conditional and excluded tools

| Candidate | Apprentice verdict | Policy |
|---|---|---|
| SideFX Labs | Allowed candidate | Install first; pin, isolate, fixture-test only the nodes used |
| MOPs open source | Allowed candidate | Install second after H22/Apple-silicon fixture validation |
| MOPs Plus | Conditional | Paid license plus concrete project justification and separate approval |
| Substance through Labs | Conditional | Verify current binary/build, Adobe terms, SBSAR asset rights, and offline behavior |
| Orbolt assets | Asset-specific | Audit license, dependencies, file type, and provenance one asset at a time |
| Python-only utilities | Conditional | Vendor into a project environment; dependency lock and network/code review required |
| HDK/native binaries | Conditional/high risk | Exact H22 ABI, Apple-silicon signature, isolated load and crash rollback required |
| Octane/Redshift/other renderers | Blocked | Apprentice does not support third-party renderers |
| Houdini Engine plugins | Blocked | Apprentice-created assets cannot be used through Engine |
| Ambient AI assistants | Blocked by default | No unrestricted code execution, hidden network activity, or opaque graph mutation |

## Roadmap

1. **Sprint 19 — World Seed Atlas (complete):** built-in terrain, ecology, USD, and comparison
   proof establishing the plugin-independent baseline.
2. **Sprint 20 — plugin governance and SideFX Labs (complete):** registry/auditor, exact approved
   install, three certified fixtures, crop-safe proof, and verified package-disabled launch.
3. **Sprint 21 — Labs-enhanced Atlas (complete):** optional capability-gated terrain, instancing,
   and curvature branches; working package-skipped native fallback; six-panel proof.
4. **Sprint 22 — MOPs kinetic reliquary (complete):** pinned isolated v1.12 audit, native plus
   three MOPs motion branches, zero-MOPs fallback, and three-frame proof.
5. **Sprint 23 — staged reliquary and perceptual verification (complete):** grid-aware
   composition and motion diagnostics plus a layered camera-facing presentation branch; human taste
   remains authoritative.
6. **Sprint 24 — bounded local visual critic (code complete, live calibration pending):**
   loopback-only Ollama adapter, exact Qwen3-VL allowlist, response schema, and mechanical corpus.
7. **Later:** APEX creature/performer studies, Pyro calligraphy, biome animation, and selective
   asset/plugin trials chosen by a concrete creative need.

Sprint 20 completed on 2026-08-24 in package `0.20.0`: the production archive exactly matches host
build `22.0.368`, its official checksum and user-scope installation are audited, enabled startup
exposes 450 matching types, three exact SOP types pass bounded graph fixtures and a 768x432 visual
proof, and the filename-qualified package skip list restores the three-node baseline. See
[`sidefx-labs-integration.md`](sidefx-labs-integration.md).

Sprint 21 completed in package `0.22.0`: the enabled Atlas passes at 4,734 points and 4,440
primitives, all six visual panels pass presence/crop checks, and a package-skipped bare-Hython
launch cooks the complete native Atlas with no plugin nodes. See
[`labs-enhanced-world-seed-atlas.md`](labs-enhanced-world-seed-atlas.md).

Sprint 22 completed in package `0.22.0`: MOPs v1.12 commit `65c4cff` is source/checksum/license
pinned, isolated from global preferences, and certified only for Plain/Noise/Shape Falloff plus
Transform Modifier. Native and three MOPs branches pass identical attribute contracts and distinct
deterministic frame digests; all twelve render panels across three frames pass mechanical visual QA.
See [`mops-kinetic-reliquary.md`](mops-kinetic-reliquary.md).

Sprint 23 completed in package `0.23.0`: presentation-only native SOP layers turn the four
verified motion contracts toward the camera and add counter-rotating inner orbits plus focal cores.
The enhanced verifier measures panel-grid composition and consecutive-frame motion. Final evidence
passes with motion across 89% of image width and 40% of height; the native-only fallback remains
plugin-free. See [`sprint23-aesthetic-verification.md`](sprint23-aesthetic-verification.md).

Sprint 24 is implemented in package `0.24.0`: the adapter is off by default, rejects non-loopback
endpoints and unlisted models, revalidates packet hashes, and cannot choose a winner. The 0.32.15
Ollama client/service has nine text models, but live inference/calibration remains pending because
no allowlisted vision model was installed or downloaded. See
[`local-vision-critic.md`](local-vision-critic.md).

## Decision

The original decision was to finish Sprint 19 natively and require separate approval before any
plugin mutation. That approval was received for Sprint 20, and the exact Labs production package is
now installed and narrowly certified. Native Houdini remains the baseline; Labs and MOPs
enhancements stay optional, capability-gated, and preserve native Switch input zero. MOPs remains
project-local rather than globally installed. Octane remains documented for a future license tier
and is not part of the Apprentice execution path.
