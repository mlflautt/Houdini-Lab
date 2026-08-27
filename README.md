# Houdini Creative Dev

A local-first **agentic Houdini development repository** for building Hermes-driven
Houdini skills and creative procedural projects — graph-first, Apprentice/non-commercial
aware, and built so the node graph stays the primary executable artifact.

This repo hosts:
- the **Hermes↔Houdini bridge** (outside-Houdini authenticated process + small inside-Houdini package),
- **graph recipes** (declarative, versioned subgraphs),
- **HDAs** (`.hdanc` source-of-truth via build scripts + tests),
- **VEX templates** (approved, curated wrangle snippets),
- **agentic skills** (manifest + module that compose tools/recipes into creative procedures),
- **creative project scaffolding** (`projects/template`).

> **Source of truth for design:** [`docs/architecture.md`](docs/architecture.md) — the
> *Hermes Houdini Apprentice: Agentic Architecture and Development Guide*, integrated here.

> **Forward roadmap:** [`docs/HERMES_HOUDINI_GRAND_PLAN.md`](docs/HERMES_HOUDINI_GRAND_PLAN.md) —
> the post-`v0.30.0` program from routine live verification through compositional projects and cross-tool
> creative handoffs.

> **Agent entry path:** [`docs/HERMES_V030_OPERATOR_RUNBOOK.md`](docs/HERMES_V030_OPERATOR_RUNBOOK.md)
> — capability discovery, intent planning, approvals, verification, hashed handoff, and dry resume.

---

## Architecture

```
Hermes conversation / project agent
        │ intent, references, constraints, approvals
        v
Hermes Houdini Orchestrator
  - procedural planner · recipe selector · context resolver
  - Apprentice policy gate · cook/render budget manager · provenance
        │ structured tool calls
        v
Local Bridge Process (outside Houdini)
  - localhost transport · schema validation · session auth
  - path allowlists · timeouts/cancellation · log aggregation
        │ bounded JSON commands
        v
Hermes Houdini Package (inside Houdini)
  - event-loop dispatcher · tool/recipe registry · stable-ID service
  - checkpoint manager · cook/cache controller · visual observer · validation
        ├──────────────┬──────────────┬──────────────┐
        v              v              v              v
Interactive Houdini  hython/background  PDG/TOP local   Project artifacts
                   jobs               jobs           (.hipnc/.hdanc/
                                                    renders/caches/USD)
```

Transport is kept separate from Houdini semantics: every operation is an ordinary typed
Python function, callable through MCP, a CLI harness, `hython` integration tests, a Python
Panel, or direct import.

---

## Quick start

### 1. Clone + install dev tooling
```bash
git clone https://github.com/mlflautt/Houdini-Lab.git
cd Houdini-Lab
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"      # ruff, pytest
```

### 2. Wire the Houdini package (inside Houdini 22, Apprentice/Indie/FX)
Install the package JSON so Houdini finds the Python lib + startup script:
```bash
# packages/hermes_houdini.json lives in ~/Library/Preferences/houdini/X.Y/packages/
# or point HOUDINI_PATH at the repo root. See packages/hermes_houdini.json.
```
On launch, `scripts/123.py` starts the in-Houdini dispatcher and registers the panel.

### 3. Run the outside-Houdini bridge (optional, for remote/agent use)
```bash
export HERMES_HOUDINI_BRIDGE_SECRET="$(python -c 'from bridge.auth import make_secret; print(make_secret())')"
export HERMES_HOUDINI_ALLOWED_ROOTS="$PWD/projects:$PWD/.hermes"
# Launch Houdini from this environment so scripts/123.py starts its localhost runtime.
python -m bridge.server --mode interactive --port 8765
python -m bridge.client --tool system.capabilities --port 8765
```

Interactive mode forwards authenticated commands to the active Houdini scene. Use
`--mode hython` explicitly for isolated read-only probes or headless jobs. See
[`docs/bridge.md`](docs/bridge.md) for ports, approvals, and failure behavior.

Medium-risk multi-node edits use the transactional `graph.apply_batch` tool. Each approved
batch creates a versioned `.hipnc` checkpoint, runs inside one undo group, returns a graph
diff, and appends an exact JSONL replay record. See [`docs/graph-kernel.md`](docs/graph-kernel.md).

Cooking is an explicit two-step job contract: submit a scope, resource estimate, policy, and
JSONL log, then run or cancel it. Geometry metrics never trigger hidden cooks. Structural
validation, headless graph SVGs, and named camera/viewer captures complete the verification
loop. See [`docs/resource-control.md`](docs/resource-control.md).

Release `v0.30.0` adds the Hermes control plane: `system.catalog`, no-cook `session.describe`,
reviewable intent plans, hashed continuation handoffs, compatibility-gated dry resume, and the
two-process relic acceptance harness. Start with the
[`v0.30 operator runbook`](docs/HERMES_V030_OPERATOR_RUNBOOK.md); release evidence is recorded in
[`docs/releases/v0.30.0.md`](docs/releases/v0.30.0.md).

Version `0.35.0` makes live verification a routine, explicit ladder. The unified
[`run_acceptance.py`](scripts/run_acceptance.py) entry point plans or executes only named tiers,
records source/build/license/package identity and bounded observations in one hashed summary, and
fails closed at separate PDG, simulation, viewport, and Karma authorization boundaries. Rebuildable
native fixtures, H22 compatibility diffs, resource baselines, the
[`operator guide`](docs/acceptance/OPERATIONS.md), and the
[`release evidence matrix`](docs/acceptance/RELEASE_EVIDENCE_MATRIX.md) keep unrun runtime, pixel,
plugin, model, and human evidence visibly distinct. The self-hosted Houdini runner remains disabled.
The integrated candidate evidence is recorded in
[`docs/releases/v0.35.0.md`](docs/releases/v0.35.0.md).

The Horizon 3 project-compiler kernel adds a pure `hermes.houdini.project.v1` specification,
versioned contract adapters, deterministic checkpointed DAG compilation, and a coherent dry
observer/drift index. Use `scripts/plan_project.py` to validate, plan, or observe the included
[`Living Biome`](projects/living_biome/README.md) fixture. These commands never start Houdini or
execute a plan. The proposed
[`G003 creative-first cycle`](docs/grinder/cycles/G003-v040-living-biome-shot/CYCLE_MANIFEST.md)
begins with three authentic motion auditions, then develops world composition, temporal design,
lookdev/presentation, and creative review as isolated lanes. Its integrated exit requires visible
still and motion evidence plus one owner-directed before/after revision; graph, cook, viewport, and
Karma remain separately authorized actions.

Any Codex, Hermes, or other harness entering for creative work should begin with
[`Creative Agent Start Here`](docs/CREATIVE_AGENT_START_HERE.md). It defines the shared
intent → alternatives → authentic preview → human critique → bounded revision → reusable-method
loop and the minimum evidence required before a visual or motion claim is considered real.

The first executable creative skill is `model.fractal_relic` (Sprint 4). It creates three
deterministic native-SOP alternatives, keeps them together in `OUT_COMPARISON`, and exposes a
human-controlled `SELECT_CANDIDATE` Switch feeding `OUT_GEO`. A run produces a checkpoint,
bounded cook log, validation metrics, graph SVG/JSON manifest, optional explicit-camera viewport
capture, empty human rating slots, replay log, and incremented `.hipnc` snapshot. The skill never
auto-ranks the alternatives.

Sprint 5 promotes that verified graph through a shared versioned source: the raw skill and
`hermes::fractal_relic::2.0` HDA both compose `sop.fractal_relic_candidate@2.0.0`. Registered
recipes instantiate as approved checkpointed batches; registered HDA builds create new `.hdanc`
files without overwriting. See [`docs/recipe-hda-system.md`](docs/recipe-hda-system.md).

Sprint 6 adds `generate.fractal_relic_variations@1.0.0`: a native Wedge → ROP Geometry local
PDG graph with one-slot scheduling, immutable plan/result manifests, per-item resource limits,
non-overwriting `.bgeo.sc` outputs, and an editable SOP comparison gallery. Local hython jobs need
exact approval and explicit external-process consent; candidates retain empty human rating slots
and are never auto-ranked. See [`docs/pdg-variations.md`](docs/pdg-variations.md).

Sprint 7 adds `simulate.vellum_relic_drop@1.0.0`: a native Cloth + Pressure Vellum graph with
named rest, constraints, collider, raw simulation, File Cache, and human-comparison contracts.
The cook controller now supports policy-bounded inclusive frame ranges, reports metrics per frame,
and restores the artist's timeline state. The skill configures but never implicitly writes its
versioned `.bgeo.sc` sequence. See [`docs/vellum-simulation.md`](docs/vellum-simulation.md).

Sprint 8 adds `lookdev.relic_stage@1.2.0`: an editable SOP Import → Material Library → three
Assign Material branches → human Switch → light/camera → Karma Render Settings LOP graph. Native
MaterialX builder subnets preserve three unranked candidates. USD stage composition is an explicit
bounded validation step; the optional one-frame Karma CPU preview is a separate approved `husk`
launch through a managed USD Render ROP and never overwrites an image. See
[`docs/solaris-lookdev.md`](docs/solaris-lookdev.md).

Sprint 9 adds `generate.differential_growth@1.0.0`: three editable native curve sources feed one
human Switch and a seeded perturbation before a Solver feedback loop. The registered loop is
Point Relax → Attribute Blur `P` → Resample; HOM constructs and tags it, while native SOPs perform
all geometry work. A 24-frame in-memory cook records rest-to-fold metrics beneath explicit
50,000-point/primitive ceilings, captures outer and inner graph evidence, and never writes a cache
or ranks a source. See [`docs/differential-growth.md`](docs/differential-growth.md).

Sprint 10 adds `generate.reaction_diffusion_pattern@1.0.0`: a Float32 Copernicus network shares
one seeded activation mask across native Small Waves, Large Waves, and Spots Gray–Scott blocks.
The graph encodes preset coefficients explicitly because Houdini's preset menu is callback-driven,
then retains mono masks, three presentation ramps, a human Switch, and a fixed-order Contact Sheet.
Bounded validation checks finite pixels, range, variance, distinct buffer hashes, memory,
resolution, and Houdini messages before managed ROP Image nodes may export new PNG evidence. See
[`docs/reaction-diffusion.md`](docs/reaction-diffusion.md).

Sprint 11 adds `grow.botanical_grammar@1.0.0`: three safe registered native L-System grammars
produce editable canopy, fern, and coral skeletons with deterministic seeds and documented turtle
attributes. Native PolyWire branches feed both a human Switch and a fixed-order comparison surface.
`botanical.validate` proves exact embedded premises/rules, topology, attributes, ordering, framing,
memory, and time while refusing arbitrary rule text or rule-file IO. The public six-generation
default remains below 250,000 points/primitives; an optional separately approved Karma reuse
provides visual proof. See [`docs/botanical-grammars.md`](docs/botanical-grammars.md).

Sprint 12 adds `motion.particle_calligraphy@1.0.0`: arc, fan, and orbit branches built from native
Particle, Time Blend, Particle Trail, Time Shift, and PolyWire SOPs. The graph visibly normalizes
legacy particle attributes and preserves a verified Houdini 22 half-frame compatibility boundary.
Its default 48-frame silent fixture records every frame under a 100,000-trail-point ceiling;
optional audio response uses only bounded project-relative envelope JSON. A new
[`verification ladder`](docs/verification-ladder.md) adds deterministic PNG mechanics and a hashed,
advisory multimodal critique packet before any local or explicitly approved external vision model.

Sprint 13 adds `simulate.vellum_membrane_lab@1.0.0`: three independently simulated pinned Grid
membranes with silk, rubber, and reinforced material profiles. Exact validation proves the anchor
mass split, Surface Struts reinforcement, per-frame motion, collision graph, cache non-writing,
comparison order, and timeline restoration. Optional viewport evidence reuses the deterministic and
hashed multimodal verification ladder. See
[`docs/vellum-membrane-lab.md`](docs/vellum-membrane-lab.md).

Sprint 14 adds `simulate.mpm_matter_sculpture@1.0.0`: three seeded native MPM Source branches with
explicit granular-like, elastic-like, and viscous-like coefficients feed one Container/Collider/
Solver graph. The safe skill is proxy-first (24 frames, 150,000 particles), records source mass and
every-frame motion/resource evidence, updates an interruption-safe progress manifest after each
frame, and leaves its File Cache in `filemode=none`. Native points and MPM Surface outputs remain
artist-selectable without implying a winner. See
[`docs/mpm-matter-sculpture.md`](docs/mpm-matter-sculpture.md).

Sprint 16 adds `world.procedural_district@1.0.0`: a registered three-profile native-SOP building
source feeds a one-slot Wedge → ROP Geometry → Wait for All TOP graph. Twelve immutable lot caches
are the safe default; exact controls, placements, hashes, and empty human ratings flow into both an
editable spatial district and a labeled no-winner gallery. Local PDG workers require explicit
external-process consent and never run in the background. Sprint 15 terrain remains optional and
deferred rather than becoming a hidden dependency. See
[`docs/procedural-district.md`](docs/procedural-district.md).

Sprint 17 adds `simulate.rbd_art_directed_fracture@1.0.0`: three retained native impact-point
profiles feed pinned Material Fracture 4.0, material Glue constraints, RBD Configure, and one
bounded proxy Bullet Solver. The compact Simulation Points output is a named transform cache
contract and reconstructs editable rest polygons through Transform Pieces. Exact 48-frame
validation checks piece/constraint budgets, finite stable transforms and hashes, broken
constraints, motion, topology preservation, cache non-writing, and timeline restoration before an
optional before/after Karma proof. See
[`docs/rbd-art-directed-fracture.md`](docs/rbd-art-directed-fracture.md).

Sprint 18 adds `lookdev.procedural_material_foundry@1.0.0`: reusable native Copernicus patterns
become twelve named `base_color`, `roughness`, `height`, and `normal` contracts, then three USD
Material COPs cross Houdini 22's Texture Material Library boundary into explicit MaterialX/USD
bindings. Equal polygon-sphere swatches keep Verdigris, Emberglaze, and Moonlichen simultaneously
visible and unranked. Numeric channel checks, full binding inspection, deterministic three-panel
visual QA, critique-packet packaging, and a crop-safe 768×432 Karma CPU proof close the stage. See
[`docs/material-foundry.md`](docs/material-foundry.md).

Sprint 19 adds `world.world_seed_atlas@1.0.0`: Amber Mesa, Verdant Rift, and Lunar Basin each use
an editable native HeightField Noise → Terrace → adaptive mesh branch, bounded biome scattering,
and one hero form. Named terrain, point, copied-form, hero, and world outputs feed three
simultaneous SOP Import LOPs. Live H22.0.368 Apprentice acceptance verified 2,442 points, 2,292
primitives, valid USD descendants, clean messages, no automatic winner, and a crop-safe 768×432
Karma CPU comparison proof. See [`docs/world-seed-atlas.md`](docs/world-seed-atlas.md).

Sprint 20 adds Apprentice-aware plugin governance and the first reversible external construction
tool integration. SideFX Labs `22.0.368` is checksum-pinned to the exact Houdini build and installed
in user package scope. The live inventory expands from three base ZibraVDB types to 450 matching
types, but certification is deliberately narrower: Measure Curvature 3.1, Terrain Analysis 1.0,
and Instance Attributes 1.0 pass readable native-input recipes, exact geometry/attribute budgets,
a saved `.hipnc`, a crop-safe 768×432 Karma proof, and a verified package-skipped launch. See
[`docs/sidefx-labs-integration.md`](docs/sidefx-labs-integration.md).

Sprint 21 adds `world.world_seed_atlas_labs@1.0.0`: each native biome receives optional Terrain
Analysis, Instance Attributes, and Measure Curvature branches using only the three Sprint 20
certified Labs types. Native remains Switch input zero. A package-skipped bare-Hython run creates
explicit `OPTIONAL_LABS_UNAVAILABLE` contracts without instantiating unknown nodes. Enabled live
acceptance produced 4,734 points/4,440 primitives and a six-panel, crop-safe 768×432 Karma proof
with no visual flags. See
[`docs/labs-enhanced-world-seed-atlas.md`](docs/labs-enhanced-world-seed-atlas.md).

Sprint 22 adds `motion.kinetic_reliquary@1.0.0`: one native packed source feeds a native transform
baseline plus MOPs 1.12 plain, animated-noise, and moving-shape falloff branches. The pinned
project-local MOPs checkout never modifies global Houdini preferences. All four 24-piece branches
preserve `P`, `orient`, `scale`, `v`, seed, and variant ID across frames 1/12/24. Three crop-safe,
color-separated 640×360 Karma proofs pass four-panel presence and nonduplicate-frame checks. A
zero-MOPs launch retains the native graph and an explicit unavailable marker. See
[`docs/mops-kinetic-reliquary.md`](docs/mops-kinetic-reliquary.md).

Sprint 23 adds `motion.kinetic_reliquary@1.1.0`: a presentation-only native SOP layer turns the
verified orbits toward the camera, adds counter-rotating inner rings and focal cores, and retains a
plugin-free native fallback. Grid composition and sampled-frame motion diagnostics now reject the
old narrow-band proof while the final four-mechanism render passes. All aesthetic ratings and winner
selection remain human-owned. See
[`docs/sprint23-aesthetic-verification.md`](docs/sprint23-aesthetic-verification.md).

Sprint 24 adds a disabled-by-default local visual critic after deterministic validation. It accepts
only an explicitly enabled IPv4-loopback Ollama endpoint and already-installed allowlisted Qwen3-VL
model, revalidates every critique-packet hash, enforces structured advisory output, and scores the
model against known mechanical failures. It never starts Ollama, downloads a model, ranks candidates,
or fills human-owned selection fields. See
[`docs/local-vision-critic.md`](docs/local-vision-critic.md).

Sprint 25 adds `verification.route@1.0.0`, a pure deterministic escalation router. It hashes
structural, visual, local-critic, and calibration evidence; blocks model overrides of mechanical
failures; checks exact model identity before trusting calibration; and emits named human-review and
external-approval routes. It executes no model or network call and never fills winner/rating fields.
See [`docs/sprint25-verification-routing.md`](docs/sprint25-verification-routing.md).

### 4. Tests
```bash
python -m pytest tests/unit -q         # pure Python, no Houdini needed
hython -m pytest tests/hython -q       # bundled recipes/skills need no injected PyYAML
```

---

## Repository layout

| Path | Purpose |
|------|---------|
| `hermes_houdini/` | Inside-Houdini package: dispatcher, graph-batch kernel, cook-job controller, observation/validation, registry, transactions, policy, stable IDs, tool impls |
| `bridge/` | Outside-Houdini authenticated JSON transport (server/client/auth) |
| `recipes/` | Declarative graph recipes (YAML) |
| `skills/` | Agentic skills: manifest + module + shared `_lib` |
| `hda/` | HDA source-of-truth (build scripts) + regression tests |
| `vex/` | Approved VEX templates |
| `panels/` | Minimal Hermes Python Panel |
| `scripts/` | `123.py` autostart, `install_panel.py` |
| `packages/` | `hermes_houdini.json` Houdini package definition |
| `tests/` | `unit/` (no Houdini), `hython/` (needs Houdini), `fixtures/` |
| `projects/template/` | Project skeleton (`project.toml` + folders) |
| `docs/` | Integrated architecture guide + conventions + apprentice constraints + curriculum |
| `manifests/` | Capability + provenance manifests |

---

## License & Apprentice note

Code here is **MIT** licensed. However, any Houdini scene (`.hipnc`) or HDA (`.hdanc`)
**produced** through this system remains governed by the **Houdini Apprentice /
Non-Commercial** license: non-commercial use only, watermarked renders, HDAs not usable
with Houdini Engine, no third-party renderers. Keep `license.mode` explicit in every
project manifest and never imply an export removes that restriction.

See [`docs/apprentice-constraints.md`](docs/apprentice-constraints.md).
