# Hermes Houdini Development Plan

- Status: integration plan completed in release `v0.25.0`
- Current integration tip: `main` at the `v0.25.0` release lineage
- Target runtime: Houdini Apprentice 22.0.368, Apple silicon, macOS

> The forward governing roadmap is
> [`HERMES_HOUDINI_GRAND_PLAN.md`](HERMES_HOUDINI_GRAND_PLAN.md). This document preserves the
> repository audit and the reasoning that led to it.

## Telos

This project is not primarily a collection of Houdini scripts. It is a local-first procedural
creative substrate that lets Hermes or another medium-sized agent translate human intent into
readable, reversible, bounded Houdini node graphs. Houdini performs geometry, simulation,
look-development, PDG, and rendering; HOM coordinates those native systems; the agent plans,
selects registered capabilities, requests approvals, preserves provenance and alternatives, and
returns both structural and visual evidence.

The durable product is the editable graph and its contracts. A render is evidence, not the source
of truth. A skill is successful only when an artist can understand, modify, compare, and continue
the result after the agent leaves.

## Architectural center

The system has four boundaries that should remain separate:

1. **Hermes orchestration** — intent translation, capability selection, policy, budgets, and
   provenance.
2. **Authenticated localhost bridge** — narrow JSON transport, replay protection, approval resume,
   path policy, cancellation, and structured results.
3. **Houdini execution package** — registered tools, recipes, skills, stable IDs, checkpoints,
   bounded cooks, observations, and validation. HOM orchestrates; native nodes compute.
4. **Evidence and handoff** — editable `.hipnc` checkpoints, graph/geometry manifests, deterministic
   image mechanics, optional advisory critics, human taste decisions, and downstream artifacts.

The implementation already has unusually broad creative coverage. The next high-leverage work is
to turn that coverage into a dependable agent-facing product boundary rather than immediately add
another isolated effect.

## Current baseline

- Sprints 0–25 cover the bridge, graph transactions, cook control, observations, recipes, HDA
  source, PDG, Vellum, MPM, RBD, Copernicus, Solaris, botanical and motion systems, procedural
  worlds, optional SideFX Labs/MOPs adapters, deterministic visual checks, a bounded local critic,
  and verification routing.
- The current tip passes 158 pure-Python tests with four expected Houdini-only skips and clean Ruff.
- Sprint 25 documentation records 33 Hython integration passes on Apprentice 22.0.368.
- Native graphs remain the fallback; plugin branches are optional and pinned.
- Human ratings and winner selection remain deliberately empty until the user decides.

## GitHub and version audit — resolved in `v0.25.0`

The audit found the following issues; each was resolved before or immediately after the `v0.25.0`
release:

| Finding | Impact | Resolution |
|---|---|---|
| `main` ends at Sprint 22 while Sprints 23–25 are three stacked PRs | Default branch and public README understate the working system | Merge the stack in order after each layer is green |
| CI was limited to PRs targeting `main` | PRs 2 and 3 received no checks because their bases are feature branches | CI now listens to every pull-request target |
| The last `main` CI run failed before the project was installed | Default-branch status is red even though the repair exists in PR 1 | Merge PR 1 first; it installs the package before testing |
| GitHub CLI credentials are invalid while SSH fetch still works | Read-only Git works, but PR retarget/merge/release operations cannot be performed safely from the CLI | Refresh `gh` authentication before GitHub mutations |
| There are no Git tags or GitHub Releases | Package `0.25.0` is not represented as a durable public release | Tag and publish `v0.25.0` only after the full stack reaches `main` |
| Package version existed in both `pyproject.toml` and `hermes_houdini/__init__.py` | Manual bumps could disagree | Use `hermes_houdini.__version__` as the packaging source of truth |
| README cloned a nonexistent historical repository name | Fresh setup instructions failed | Point clone instructions at `mlflautt/Houdini-Lab` |
| Extra license prose made GitHub report `NOASSERTION` | Public license metadata did not match the intended MIT code license | Keep `LICENSE` canonical; retain the Houdini artifact boundary in README and Apprentice docs |

### Safe integration sequence

Do not squash the entire stack into one opaque change and do not force-push. Preserve the
acceptance lineage already recorded in each sprint.

1. Refresh GitHub CLI authentication and confirm the active account and repository.
2. Merge PR 1 (`sprint-23`) into `main` after its green CI result.
3. Retarget PR 2 (`sprint-24`) to `main`; wait for CI; merge it.
4. Retarget PR 3 (`sprint-25`) to `main`; wait for CI; merge it.
5. Run CI on the resulting `main`, fetch it locally, and compare `main` to the validated Sprint 25
   tip.
6. Create annotated tag `v0.25.0` and a GitHub Release summarizing Sprints 23–25 and their evidence.
7. Delete the three merged remote sprint branches, then prune remote-tracking refs locally.
8. Confirm GitHub identifies the MIT license and that the README clone/install path works in a
   disposable directory.

Completion evidence: all three PRs merged in order, final `main` CI passed, `v0.25.0` was tagged and
released, merged branches were removed, GitHub recognizes MIT, and the single-owner protection rule
now requires PRs plus strict CI without an impossible outside approval.

## Development priorities

### P0 — Stabilize integration and release discipline

Outcome: `main` is the trustworthy public integration branch and every release is reconstructible.

- Complete the merge sequence above.
- Keep package SemVer independent from sprint numbering. Skills, recipes, HDAs, protocol, and
  external plugins each retain their own versions.
- Add a short changelog/release-note template with compatibility fields: Houdini build, license
  mode, Python, plugin pins, tests, live-Hython evidence, visual evidence, and known pending gates.
- Treat a Git tag as a source release, not as proof that live Houdini or creative review passed;
  link the exact evidence separately.
- Add a release check that asserts the package version, import version, tag, built wheel metadata,
  and capability manifest agree.

Acceptance: a fresh clone of `v0.25.0` installs, passes pure tests, enumerates the expected tools,
recipes, and skills, and links to the preserved Hython and visual evidence.

### P1 — Productize the Hermes orchestration boundary

Outcome: Hermes can discover and execute the existing system without reading the whole repository
or inventing raw graphs.

- Generate a compact, versioned capability catalog from registered tools, recipes, HDAs, and skill
  manifests. Include context, risk, approvals, inputs, outputs, cook budgets, tested builds,
  license, optional dependencies, fallback, and evidence status.
- Define a session-bootstrap response: system/build/license/package inventory, open HIP, `$JOB`,
  allowed roots, active bridge mode, available capabilities, and pending approvals/cooks.
- Add a planner-facing selection contract that ranks capabilities by applicability and safety, not
  by aesthetic quality. Preserve all creative candidates for human selection.
- Add an execution transcript/handoff schema that another Hermes or Codex session can replay or
  continue: intent, selected skill/version, resolved IDs/paths, approvals, checkpoints, cooks,
  artifacts, warnings, rejected alternatives, and human feedback.
- Publish one end-to-end Hermes runbook using a representative existing skill before adding a new
  effect.

Acceptance: a clean local agent session can inspect capabilities, plan a bounded run, obtain the
required approval, execute one skill in Houdini, verify it structurally and visually, save a
checkpoint, and hand the project to a second session without hidden UI state.

### P2 — Make live Houdini verification routine

Outcome: pure-Python CI and live Houdini evidence are clearly distinct, repeatable gates.

- Keep fast pure tests on every PR.
- Design a locked-down self-hosted macOS/Houdini runner profile, but enable it only after reviewing
  repository trust, secrets, license behavior, process isolation, cache limits, and cleanup.
- Until that runner is approved, provide one local acceptance entry point that runs the intended
  Hython suite, records the exact Houdini build/license, and emits a signed or hashed summary.
- Split integration tests into read-only, graph-edit, cook, PDG child-process, simulation, and
  render tiers so expensive or external work requires the corresponding gate.
- Maintain small golden fixtures and visual calibration cases. Do not commit `.hipnc` binaries as
  source; retain build recipes and manifests.

Acceptance: every PR shows pure-test status, while release notes separately state whether current
build Hython, render, plugin-enabled, plugin-disabled, and human-review gates passed or remain
pending.

### P3 — Continue creative development through compositions

Outcome: new work demonstrates composition of the substrate rather than another disconnected
single-domain demo.

Choose the next study with the user; do not auto-rank these directions:

- **APEX procedural performer:** build a small rigged procedural creature or instrument with named
  animation contracts and a native fallback.
- **Pyro calligraphy:** turn the existing particle-calligraphy paths into bounded sparse-Pyro
  sources, preserving the original curves and a simulation-bypassed branch.
- **Living biome shot:** compose World Seed terrain, botanical grammar, materials, motion, and one
  optional bounded simulation into a short Solaris shot.
- **Cross-tool handoff:** package Houdini USD/render passes and provenance for Blender or DaVinci
  Resolve without claiming downstream conform or review until it is actually performed.

For any direction, start with a human-readable hypothesis, references, rules, costs, and success
conditions. Preserve alternatives and ask the user to select taste winners.

## Recommended next milestone

Call the next milestone **Hermes End-to-End Composition**, not Sprint 26 by default. Its purpose is
to prove the control plane across an existing creative capability:

1. Generate the capability catalog and session bootstrap.
2. Start the authenticated localhost bridge in interactive mode.
3. Have Hermes select and plan one existing skill from intent plus explicit constraints.
4. Execute through approval, checkpoint, bounded cook, structural checks, and a 768×432 visual
   proof.
5. Produce a continuation handoff and resume it in a fresh agent session.
6. Record human critique and a user-selected continuation; do not synthesize an aesthetic winner.

This milestone closes the largest architectural gap: the repository contains many mature
capabilities, but the documented Hermes-facing discovery, planning, and continuation loop has not
yet been proven as one repeatable product path.

## Definition of done

A development increment is complete only when it has:

- a narrow purpose and versioned contract;
- exact Houdini category, parent, and operator types;
- safe defaults, stable Hermes IDs, checkpoint, rollback, and path policy;
- declared cook/process/memory/render scope and approvals;
- a readable editable graph with named inputs, outputs, alternatives, and fallback;
- deterministic structural/data checks plus authentic viewport or Karma evidence when applicable;
- pure tests and proportionate live-Hython evidence;
- Apprentice/license/build/plugin provenance;
- a continuation handoff suitable for Hermes and Codex;
- explicit pending status for any unrun live, visual, external, or human gate.

The final authority for creative taste remains the user.
