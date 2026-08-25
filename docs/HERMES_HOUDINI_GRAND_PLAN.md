# Hermes Houdini Grand Development Plan

- Status: governing roadmap after the `v0.25.0` integration release
- Planning horizon: control plane → creative compositions → cross-tool studio
- Runtime baseline: Houdini Apprentice 22.0.368, Apple silicon, macOS
- License baseline: personal, educational, non-commercial

## North star

Build a creative operating system in which Hermes, Codex, or a capable local agent can enter a
Houdini project, understand what exists, propose a bounded procedural plan, construct a readable
native node graph, prove what it made, receive human artistic direction, refine without destroying
alternatives, and leave a complete continuation package for the next artist or agent.

The project succeeds when agentic work feels like collaboration with a disciplined procedural
artist—not remote control of a Python console.

## What has shipped

Release `v0.25.0` establishes a substantial substrate:

- 65 registered tools spanning inspection, graph mutation, transactions, cooking, observation,
  simulation, PDG, Solaris, plugin governance, and verification;
- 30 versioned graph recipes across SOP, COP, LOP, and TOP contexts;
- 17 agentic creative skills;
- 137 explicit unit-test functions, producing 158 passing cases at the release acceptance gate;
- 33 Hython integration tests under the pinned Houdini build;
- an authenticated loopback bridge with replay protection and approval resume;
- stable Hermes IDs, path policy, checkpoints, rollback, bounded cooks, and replay logs;
- editable studies in procedural modeling, Copernicus, Vellum, MPM, RBD, particles, botanical
  grammars, materials, Solaris, PDG districts, procedural worlds, and motion graphics;
- optional, pinned, reversible SideFX Labs and MOPs integrations with native fallbacks;
- deterministic pixel mechanics, a bounded local critic adapter, and evidence routing that cannot
  override mechanical failures or choose an aesthetic winner.

The repository is no longer missing raw capability. Its primary gap is turning those capabilities
into one discoverable, repeatable, end-to-end Hermes creative workflow.

## Governing doctrine

Every roadmap decision must preserve these invariants:

1. **Graph-first.** Native Houdini nodes and readable compositions are the executable source of
   truth. Code supports the graph; it does not conceal it.
2. **HOM orchestrates; Houdini computes.** Never move large geometry loops into Python for agent
   convenience.
3. **Intent becomes contracts.** Context, inputs, outputs, attributes, seed, versions, budgets,
   license, and evidence are explicit.
4. **No hidden UI state.** Selection, pane, desktop, frame, and display flags are never implicit
   dependencies.
5. **Non-destructive exploration.** Branch, Switch, Null, checkpoint, cache boundary, and bypass
   precede replacement or deletion.
6. **Cooking is a resource decision.** Editing, one-node cooking, frame ranges, PDG work, simulation,
   and rendering are different approvals and budgets.
7. **Proof is layered.** Schema and graph checks do not substitute for cooked data; data does not
   substitute for authentic pixels; pixels do not substitute for human taste.
8. **Human taste remains sovereign.** Agents may diagnose and propose; they may not silently fill
   ratings, choose winners, or erase rejected lineages.
9. **Native fallback first.** Plugins enhance named contracts and remain optional, pinned, and
   reversible.
10. **Truthful public artifacts.** Release notes state exactly which pure, Hython, live-Houdini,
    visual, plugin, external-model, and human gates actually ran.

## Target system

```text
human intent + references + constraints + feedback
                         |
                         v
Hermes creative planner and session memory
  - capability discovery
  - intent decomposition
  - risk/license/resource policy
  - alternative and taste provenance
                         |
                         v
authenticated localhost control plane
  - session bootstrap
  - typed commands and approvals
  - cancellation, replay protection, logs
                         |
                         v
Houdini graph execution substrate
  - native nodes, recipes, HDAs, skills
  - stable IDs, checkpoints, bounded cooks
  - plugin-capability adapters and fallbacks
                         |
                         v
evidence, critique, refinement, and handoff
  - graph/data/pixel/runtime evidence
  - human comparisons and exact feedback
  - USD/render/cache/project continuation bundle
                         |
                         v
Blender / DaVinci Resolve / Music Lab / archival pipeline
```

Transport, Houdini semantics, creative planning, and evidence remain separate boundaries. This
keeps the system usable from a CLI, Python Panel, MCP adapter, Hython harness, or future local-agent
runtime without coupling creative logic to one interface.

## Version 1.0 success condition

Version 1.0 is not “every Houdini feature supported.” It is the point where a fresh agent can:

1. discover the live build, license, scene, packages, allowed roots, budgets, and capabilities;
2. translate a user brief into a reviewable procedural plan using registered capabilities;
3. explain the creative hypothesis, alternatives, action costs, and expected evidence;
4. request only the approvals required by the chosen graph/cook/render path;
5. build or refine an editable graph without relying on hidden UI state;
6. survive interruption through checkpoints, replay records, and resumable handoff state;
7. prove graph structure, cooked data, pixels, and runtime behavior at the appropriate gates;
8. present meaningful alternatives without automatic taste ranking;
9. incorporate exact human criticism into a new, preserved iteration;
10. export a provenance-rich downstream package and resume it in another agent session;
11. reproduce the accepted result on the pinned Houdini build from repository sources;
12. clearly mark every unrun or unavailable gate as pending, partial, warning, or blocked.

## Program structure

Development proceeds through nine horizons. Release numbers are directional bands, not promises;
acceptance evidence—not calendar time—advances the project.

### Horizon 0 — Repository and release substrate (`v0.25`, complete)

Outcome: a trustworthy `main`, protected PR workflow, green pure CI, canonical MIT metadata,
versioned source release, and cleaned branch history.

Remaining maintenance:

- add release metadata validation that compares tag, package import version, wheel metadata,
  capability catalog version, Houdini build, and evidence status;
- add a compact changelog/release template;
- keep pure CI fast and keep live Houdini claims separate.

Exit evidence: `v0.25.0`, final-main CI, three merged PRs, clean main, and published release notes.

### Horizon 1 — Hermes control plane (`v0.30`, complete)

Outcome: an agent can discover and operate the existing system without reading the repository or
inventing raw node graphs.

Deliverables:

1. **Capability catalog schema**
   - generated from registered tools, recipes, HDAs, and skill manifests;
   - includes context, exact version, risk, approvals, I/O, attribute contracts, cook budgets,
     license, tested builds, optional dependencies, fallback, and evidence state;
   - deterministic JSON with a content hash and compatibility version.
2. **Session bootstrap**
   - reports Houdini build/license, Python, open HIP, `$JOB`, package inventory, allowed roots,
     bridge mode, active frame/range, pending approvals, cooks, and managed nodes;
   - never cooks geometry merely to describe the session.
3. **Intent-to-capability plan contract**
   - stores user objective, references, constraints, selected capabilities, alternatives, resource
     estimates, approvals, and verification plan;
   - ranks applicability and safety only, never creative taste.
4. **Continuation handoff bundle**
   - captures selected skill/recipe versions, stable IDs/paths, checkpoint, replay log, artifacts,
     hashes, pending gates, warnings, rejected alternatives, and exact human feedback;
   - validates without Houdini and resumes with explicit build-drift warnings.
5. **Agent runbook**
   - one compact operating guide suitable for Hermes or another medium local model;
   - prioritizes registered calls and bounded decisions over repository-wide code synthesis.

Reference acceptance: run `model.fractal_relic` as the small deterministic system test. It is not
an aesthetic winner; it is the cheapest capability that exercises discovery, planning, approval,
checkpoint, graph construction, bounded cook, visual proof, alternatives, and handoff.

Exit evidence: a clean agent session completes the loop and a second fresh session resumes it
without hidden state, repository archaeology, or automatic execution. Release `v0.30.0` passed this
gate on Houdini Apprentice 22.0.368 with
an authenticated loopback bootstrap, one bounded Karma proof, a hashed handoff, and 46/46 stable IDs
resolved in the second process; human aesthetic review remains explicitly pending.

### Horizon 2 — Live verification as routine infrastructure (`v0.35` candidate)

Outcome: every claim has a named evidence rung and live Houdini validation becomes repeatable rather
than artisanal.

Deliverables:

- one `scripts/run_acceptance.py` entry point with explicit tiers: pure, read-only Hython, graph
  edit, single-frame cook, frame range, PDG child process, simulation, viewport, and Karma;
- hashed acceptance summaries containing build, license, package inventory, command, duration,
  budgets, artifacts, and pass/warn/pending/blocked status;
- fixture builders for small `.hipnc` scenes, with source-of-truth remaining recipes/build scripts;
- performance baselines for points, primitives, memory, cook time, cache bytes, frames, and render
  resolution;
- current-build compatibility probes that fail with useful operator/parameter diffs;
- a locked-down self-hosted Houdini runner design covering repository trust, local credentials,
  license behavior, cleanup, process isolation, caches, concurrency, and artifact retention;
- no self-hosted runner activation until that threat model and operational cost are approved.

Exit evidence: a release matrix clearly distinguishes pure CI, live Hython, interactive Houdini,
plugin-enabled/disabled, render, local-model, external-model, and human-review status.

### Horizon 3 — Project compiler and compositional graphs (`v0.40` candidate)

Outcome: existing skills compose into coherent projects rather than remaining an anthology of
individual studies.

Deliverables:

1. **Project specification** — a versioned, human-readable project file declaring creative brief,
   references, license, seed policy, asset roots, chosen capability versions, variants, timeline,
   budgets, evidence gates, output contracts, and human decision slots.
2. **Contract adapters** — small native recipes that connect named outputs between skills without
   flattening or copying whole graphs.
3. **Project compiler** — resolves the specification into a checkpointed execution DAG with a dry
   plan, explicit cook stages, stable IDs, and resumable state.
4. **Project observer** — emits one coherent graph/evidence/provenance index across SOP, COP, LOP,
   TOP, cache, render, and handoff artifacts.
5. **Dependency and drift report** — exact Houdini/plugin/operator requirements plus native fallback
   coverage before execution.

Reference creative study: **Living Biome Shot**. Compose World Seed terrain, procedural materials,
botanical grammar, one motion system, Solaris staging, and one optional bounded simulation into a
short shot. Preserve three equal-status biome directions and ask the user which lineage to continue.

Exit evidence: rebuild the project from its specification and source recipes; compare hashes and
declared tolerances; open a readable scene in which an artist can continue every major layer.

### Horizon 4 — Human-guided refinement and creative memory (`v0.50` candidate)

Outcome: the system improves through exact user guidance without laundering taste into automatic
scores.

Deliverables:

- immutable feedback records that bind exact user words to exact candidate/artifact/span IDs;
- a revision planner that converts criticism into bounded graph, parameter, framing, material,
  timing, or evidence hypotheses;
- before/after lineage with rejected attempts preserved and rollback always available;
- comparison packets with stable ordering and no implied winner;
- explicit `human_rating`, `selected_for_continuation`, and `why` fields owned only by the user;
- project-local taste notes separated from universal mechanical rules;
- a handoff summary that tells the next agent what the user liked, disliked, rejected, and has not
  yet judged.

Exit evidence: perform two user-led revision cycles on one composition. Show that a new agent can
apply the feedback consistently without reversing A/B identity or overwriting the rejected branch.

### Horizon 5 — Advanced creative verticals (`v0.60` candidates)

Outcome: expand Houdini fluency through a small number of deep, graph-readable compositions.

These directions are alternatives for human selection, not an automatic priority ranking:

| Direction | Core Houdini systems | Required proof |
|---|---|---|
| APEX procedural performer | KineFX/APEX, SOP rig construction, clips, constraints, Solaris | editable rig contracts, pose/motion validation, short authentic animation proof |
| Pyro calligraphy | existing particle paths, sparse Pyro, volumes, cache, Karma | source-curve preservation, bypassed native path, bounded voxel/frame proof |
| Matter ritual | MPM + RBD + Vellum composition | staged solver budgets, cache boundaries, interaction evidence, readable subsystem graph |
| Living district | terrain, district PDG, botanical/material systems, USD instancing | bounded work items, terrain-aware placement, no-winner world comparison |
| Procedural instrument sculpture | CHOP/audio envelope, motion, materials, USD | baked-envelope provenance, silent fallback, temporal and audiovisual review |
| Data-driven world | external approved dataset → attributes → geometry/materials | data license, schema provenance, deterministic mapping, no hidden network dependency |

Each vertical must reuse the control plane, project compiler, evidence ladder, and handoff format.
No vertical may create a private second orchestration system.

Exit evidence: at least two distinct verticals prove that the architecture generalizes beyond the
reference composition while remaining editable and Apprentice-safe.

### Horizon 6 — Cross-tool creative studio (`v0.70` candidate)

Outcome: Houdini becomes a dependable procedural upstream for Blender, DaVinci Resolve, Music Lab,
and archival workflows.

Deliverables:

- a versioned handoff package containing USD/geometry, textures, render passes, cameras, frame
  ranges, color-space intent, audio-envelope lineage, license, hashes, and reconstruction notes;
- consumer profiles for Blender and Resolve that state what each tool can ingest and what remains
  unverified;
- downstream receipt manifests that record actual import/conform/render results rather than
  assuming a file export succeeded creatively;
- image-sequence and render-pass contracts suited to Resolve without claiming a live conform until
  Resolve is run and reviewed;
- optional Music Lab envelopes and event markers while keeping TidalCycles/SuperCollider as the
  music-creation core;
- one cross-tool project resumed by a different agent with no missing provenance.

Exit evidence: Houdini → one downstream tool → reviewed output → continuation handoff, with
structural and audiovisual proof kept distinct.

### Horizon 7 — Scale, resilience, and controlled variation (`v0.80` candidate)

Outcome: larger projects remain bounded, interruptible, recoverable, and curator-friendly.

Deliverables:

- resumable PDG project stages with immutable work-item manifests and bounded local concurrency;
- cache identity, staleness, quota, and garbage-collection policy that never deletes artist data
  without approval;
- crash/interruption recovery tests across graph edits, simulations, PDG, and renders;
- deterministic variation families with fixed lineage and empty human-rating slots;
- contact sheets and review queues that help humans curate without machine taste promotion;
- performance regression dashboards based on project-owned metrics, not opaque telemetry;
- security review for bridge exposure, dependency supply chain, plugin updates, and external-model
  packets.

Exit evidence: interrupt and resume a multi-stage project without duplicated work, stale outputs,
lost alternatives, or silent budget overruns.

### Horizon 8 — Version 1.0 and optional license expansion

Outcome: a stable agentic Houdini studio with a documented upgrade path beyond Apprentice.

Version 1.0 gates:

- stable public schemas and compatibility policy for commands, capabilities, projects, handoffs,
  and evidence;
- migration tools for at least the previous two minor schema generations;
- clean installation and removal instructions;
- pinned Houdini-build compatibility matrix and failure reports;
- reproducible reference projects with authentic visual/runtime evidence;
- threat model and permission review;
- complete operator/artist continuation documentation;
- at least one Hermes-driven and one Codex-driven end-to-end acceptance;
- a human playtest/creative review showing the workflow is understandable, not merely executable.

Indie/FX, Houdini Engine, commercial output, third-party renderers, farm/cloud execution, or external
asset services remain separate license and security programs. They begin only after an explicit
license upgrade and do not weaken the Apprentice-safe native path.

## Immediate execution program

The next release should be narrow: **Hermes End-to-End Control Plane (`v0.30`)**.

### First ten pull requests

1. Add pure schemas for capability catalog, evidence status, and compatibility identity.
2. Generate the catalog from tool/recipe/HDA/skill registries and lock deterministic ordering.
3. Expose `system.catalog` with filtering by context, risk, license, build, and dependency.
4. Add pure session-bootstrap schema and a read-only `session.describe` tool.
5. Add intent-plan schema with explicit alternatives, estimates, approvals, and verification route.
6. Add continuation-handoff schema, hashing, validation, and path policy.
7. Add `handoff.create`, `handoff.inspect`, and `handoff.resume_plan` without automatic execution.
8. Add a compact Hermes operator runbook and example prompts based on registered calls.
9. Add a disposable end-to-end acceptance harness using `model.fractal_relic`.
10. Run live Apprentice acceptance, capture authentic evidence, fix discovered friction, and release
    `v0.30.0` only when a fresh second session resumes successfully.

Each PR must be independently useful, pure-testable where possible, and small enough that a medium
local agent can understand the change.

### `v0.30` acceptance transcript

The release evidence should tell one complete story:

1. Start from a clean clone and a disposable project root.
2. Start Houdini Apprentice 22.0.368 and the authenticated bridge.
3. Call `session.describe` and `system.catalog` without cooking.
4. Give Hermes a short creative brief and explicit resource constraints.
5. Produce a dry plan showing selected capability, preserved alternatives, risk, approvals, and
   evidence route.
6. Approve the medium-risk graph batch.
7. Create the graph inside one checkpointed transaction.
8. Cook one bounded frame and record geometry metrics.
9. Capture a real viewport or Karma proof at a conservative resolution.
10. Leave ratings empty, record the user's exact response, and create a continuation handoff.
11. End the session.
12. Start a new session, validate the handoff, resolve stable IDs, and propose—not automatically
    execute—the next refinement.

Failure at any rung becomes evidence for improving the control plane; it is not patched over by a
larger monolithic script.

## Evidence ladder and release gates

Every feature declares which gates apply:

| Gate | Question | Normal evidence |
|---|---|---|
| G0 Schema | Is the request/result structurally valid? | pure tests, schema fixtures |
| G1 Policy | Is it allowed in this mode, path, license, and budget? | deterministic policy report |
| G2 Graph | Is the intended readable graph present? | node types, connections, stable IDs, graph SVG |
| G3 Data | Did the correct data cook within limits? | geometry/field/USD/frame metrics |
| G4 Pixels | Do authentic pixels show the claimed output? | viewport/flipbook/Karma plus mechanics |
| G5 Runtime | Did live Houdini/plugin/process behavior actually work? | pinned-build Hython or interactive log |
| G6 Human | Is the result understandable and artistically useful? | exact feedback, rating, selected continuation |
| G7 Handoff | Can another session/tool continue it? | validated bundle and downstream receipt |

Statuses are `pass`, `warn`, `pending`, `blocked`, or `not_applicable`. Structural success never
silently upgrades an unrun visual, runtime, external, or human gate.

## Release and GitHub discipline

- `main` remains protected by required PRs, strict unit CI, conversation resolution, no force-push,
  and no branch deletion.
- The single-owner repository requires zero outside approvals; administrators remain subject to
  protection.
- Auto-merge may be used only after required checks pass. Merged head branches are removed.
- Prefer merge commits when preserving coherent milestone lineage. Never force-push collaborative
  work.
- Package SemVer is independent from sprint/horizon labels. Tools, recipes, skills, HDAs, schemas,
  protocol, Houdini builds, and plugins keep their own versions.
- A release note lists pure CI, Hython, interactive, plugin, render, model, human, and handoff status
  separately.
- Release artifacts never imply that Apprentice-generated content became commercially licensed.
- Public previews use authentic runtime captures and label generated concept imagery as concept
  imagery.

## Risk register

| Risk | Consequence | Control |
|---|---|---|
| Capability breadth outruns orchestration | many demos, no dependable agent workflow | freeze new verticals until `v0.30` end-to-end loop passes |
| Houdini build drift | renamed nodes/parameters and false compatibility | exact build identity, live probes, versioned adapters |
| Hidden cooking | latency, memory pressure, unintended writes | cook scopes, budgets, submission/run split, non-writing defaults |
| Monolithic generated Python | opaque and fragile scenes | registered recipes, native nodes, small reviewed orchestration functions |
| Aesthetic automation overreach | user intent and alternatives are erased | human-owned ratings, immutable lineage, advisory critics only |
| Plugin contamination | unreadable scenes or broken startup | native input zero, pinned package roots, skip-list rollback, narrow certification |
| False proof | structure passes while visuals/runtime fail | evidence ladder with independent statuses |
| Agent handoff loss | duplicated or contradictory work | versioned handoff bundle, stable IDs, exact feedback, pending gates |
| Self-hosted runner exposure | local credentials or machine compromise | threat model, trusted refs only, isolation, no activation by default |
| Cross-tool optimism | exported files are claimed as finished work | consumer receipt and actual downstream review required |
| Apprentice license leakage | non-commercial artifacts enter commercial pipeline | explicit license in every project, handoff, and release manifest |
| Project complexity becomes illegible | artist cannot continue the graph | named contracts, network boxes, subsystem observers, human comprehension gate |

## Human decision gates

The user retains explicit control over:

- which advanced creative vertical begins after the control-plane milestone;
- which candidate or lineage continues;
- whether optional plugins, model downloads, external critics, network services, or self-hosted CI
  are installed or enabled;
- whether higher cook/render/cache budgets are justified;
- whether a project may cross into another tool or external provider;
- whether the Houdini license tier changes;
- what counts as artistically successful.

The system should bring these decisions to the user with enough evidence to be meaningful, not ask
them to debug missing nodes, black frames, or broken contracts.

## Definition of done for the grand plan

The roadmap has achieved its purpose when the repository is no longer best described as a set of
agentic Houdini experiments. It should be demonstrably usable as a creative practice:

- a new agent can orient quickly;
- a human can understand the objective and costs before execution;
- Houdini graphs remain readable and editable;
- interruption and iteration are safe;
- evidence is authentic and proportional;
- taste stays human-owned;
- another session or tool can continue the work;
- public claims match what actually ran.

The immediate move is therefore not “Sprint 26: another effect.” It is **Hermes End-to-End Control
Plane**, followed by the first genuinely compositional project.
