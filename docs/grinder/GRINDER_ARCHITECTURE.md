# Grinder Architecture

- Architecture version: `1.0`
- Applies to: parallel development of Hermes Houdini capabilities
- Governing repository architecture: [`../architecture.md`](../architecture.md)
- Governing roadmap: [`../HERMES_HOUDINI_GRAND_PLAN.md`](../HERMES_HOUDINI_GRAND_PLAN.md)

## Telos

The Grinder lets several capable agents develop one coherent creative system without relying on
shared chat memory, accidental sequencing, or heroic integration. It should make parallel work
faster while preserving the qualities the project exists for: graph-readable Houdini systems,
bounded resource use, reversibility, truthful evidence, creative alternatives, and clean handoff
between Hermes, Codex, local agents, and human artists.

The unit of success is not "a lane wrote code." A cycle succeeds when its combined result crosses a
named repository gate from an immutable baseline and leaves enough evidence for a fresh agent to
reproduce, inspect, and continue it.

## Two control planes

```text
Grand roadmap
    |
    v
Grinder control plane (repository development)
  cycle manifest -> parallel lanes -> receipts -> integration train -> release gate
                                                    |
                                                    v
Hermes/Houdini control plane (creative execution)
  intent -> registered capability -> graph/cook/render -> evidence -> handoff
```

The Grinder may organize changes to the runtime control plane, but it must not bypass runtime
policy. A development lane cannot use its assignment as approval for destructive Houdini edits,
large simulations, network access, plugin installation, or publication.

## Core records

### Program

The grand plan defines the north star, horizons, and evidence required to advance a release band.
It changes slowly and does not become an agent's improvised task list.

### Cycle

A cycle is an accepted, immutable execution contract containing:

- one base tag and full commit SHA;
- one target horizon and explicit non-goals;
- a dependency DAG;
- lane-owned file paths and shared-file prohibitions;
- integration order and integration-owned files;
- required tests and evidence rungs;
- stop conditions, amendment rules, and release authority.

### Lane

A lane is the smallest independently reviewable branch. Its brief contains all project context,
commands, contracts, files, tests, and handoff requirements needed by a fresh Codex instance.
Lanes never depend on conversation state or uncommitted files from another lane.

### Receipt

Every lane commits a machine-readable-enough Markdown receipt. It records the actual base, head,
changed files, tests, evidence status, deviations, and unresolved integration work. "All tests
pass" without exact commands and results is not a receipt.

### Integration train

The integration captain combines lane heads in manifest order, resolves only declared integration
seams, runs the union of gates, updates shared metadata, and opens the release PR. The captain does
not silently redesign a failed lane. A contract mismatch returns to the owning lane or becomes an
explicitly documented integration amendment.

## Lifecycle

```text
PROPOSED -> ACCEPTED -> DISPATCHED -> LANE_READY -> INTEGRATING -> VERIFIED -> RELEASED
               |             |            |              |
               +----------> BLOCKED <------+--------------+
```

- `PROPOSED`: reviewable plan; no lane should begin implementation.
- `ACCEPTED`: human owner has frozen the baseline and lane contracts.
- `DISPATCHED`: isolated worktrees/branches exist and briefs have been assigned.
- `LANE_READY`: a lane has a pushed commit, receipt, and required green gates.
- `INTEGRATING`: the captain is assembling accepted lane heads.
- `VERIFIED`: the integrated head passed every required automated gate; unavailable human or
  external gates remain explicitly pending.
- `RELEASED`: protected-branch integration and release publication are complete.
- `BLOCKED`: a concrete unmet dependency, policy approval, or failed contract prevents progress.

Only the human owner can move `PROPOSED` to `ACCEPTED`, approve manifest amendments, authorize
external/high-risk actions, and accept human-review evidence. Agents may move technical work among
the other states through committed receipts and PR evidence.

## Parallelism rules

1. **Immutable base.** Every lane begins at the manifest's full base SHA, even if `main` moves.
2. **One writer per path.** Parallel lanes have disjoint owned paths. Directory ownership does not
   imply ownership of existing files unless the manifest lists them.
3. **Shared hotspots are integration-only.** Package versions, exports, registries, root README,
   changelog, roadmap, workflows, and release notes belong to the captain.
4. **Contracts before consumers.** If one lane consumes another's interface, the manifest includes
   a frozen contract or makes the consumer an integration task. No lane imports an unpublished
   sibling implementation.
5. **No cross-lane pulls.** Lanes do not merge, rebase, or cherry-pick other lane branches. This
   preserves attribution and prevents invisible dependency drift.
6. **No force pushes.** Each lane pushes an ordinary branch and opens a PR against the manifest's
   integration branch or the repository's chosen protected flow.
7. **Truthful gates.** Pure, Hython, graph edit, cook, simulation, render, plugin, model, and human
   review are distinct. An unrun rung is `pending`, never inferred from a lower rung.
8. **Preserve lineage.** Failed probes and rejected creative candidates remain identified. Agents
   do not manufacture a taste winner to make a gate green.

## Branch and worktree convention

For cycle `GNNN`, use:

- integration branch: `codex/grinder-gnnn-integration`
- lane branches: `codex/grinder-gnnn-<lane>-<slug>`
- planning branch: `codex/grinder-architecture` or a cycle-specific planning branch

Prefer one separate Git worktree or clone per Codex instance. Each instance must print and record:

```bash
git rev-parse --show-toplevel
git status --short --branch
git rev-parse HEAD
git remote -v
```

The lane stops if its starting HEAD does not equal the manifest's full SHA or if the worktree is
dirty before lane work begins.

## File ownership and merge seams

A cycle manifest contains three sets:

- **lane-owned:** files the lane may add or edit;
- **read-only context:** files the lane should study but must not edit;
- **integration-owned:** shared files only the captain may change.

Generated artifacts, caches, virtual environments, `.hipnc` files, and evidence too large or
machine-specific for Git remain outside commits unless the manifest explicitly makes them release
artifacts. Binary Houdini scenes are never the source of truth.

## Evidence model

Each gate records `pass`, `warn`, `pending`, `blocked`, or `not_applicable` plus its exact command,
environment, duration where meaningful, and artifact path/hash where applicable.

The minimum lane gate is:

1. scope check (`git diff --name-only <base>...HEAD`);
2. targeted tests;
3. full pure tests;
4. Ruff;
5. relevant Hython or live evidence if the lane makes a Houdini claim;
6. receipt completeness.

The minimum integrated gate is the union of all lane gates plus clean-install import, complete
Hython suite, required visual/runtime proofs, release metadata consistency, and final-main CI.

## Amendments and stop conditions

Stop and report instead of improvising when:

- a required operator/parameter is absent on the pinned Houdini build;
- a lane must edit a path owned by another active lane;
- a required dependency needs network access, global installation, or unclear licensing;
- a test failure predates the lane or contradicts the frozen contract;
- executing the brief would require destructive, over-budget, or externally privileged work;
- the baseline SHA, tag, or expected repository shape does not match.

A manifest amendment states the reason, affected lanes, new ownership, migration action, and human
approval. It is committed before affected work resumes.

## Cycle sizing

Use a cycle when the integrated outcome can be accepted as one coherent release gate. Prefer three
to five build lanes; beyond that, coordination cost usually exceeds useful parallelism. A lane
should fit one independent Codex task and produce one reviewable PR. Sequential work belongs in the
integration lane or the next cycle.

