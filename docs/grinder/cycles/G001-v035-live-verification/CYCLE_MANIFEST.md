# Grinder Cycle G001 — v0.35 Live Verification Infrastructure

- State: `ACCEPTED — LANES A-D AUTHORIZED`
- Manifest version: `1.0`
- Proposed on: `2026-08-25`
- Accepted on: `2026-08-25`
- Acceptance instruction: `Accept Grinder Cycle G001 and launch lanes A-D from v0.30.0.`
- Target horizon: Horizon 2, `v0.35` candidate
- Repository: `mlflautt/Houdini-Lab`
- Base tag: `v0.30.0`
- Base commit: `b8b8f4c4b702b4f895bbee3098c90006541a7373`
- Integration branch after acceptance: `codex/grinder-g001-integration`
- Target runtime: Houdini Apprentice `22.0.368`, Apple silicon, macOS
- Conservative render ceiling: `1280x720`, Karma CPU

## Launch authority

The human owner accepted and froze this cycle with:

> Accept Grinder Cycle G001 and launch lanes A-D from v0.30.0.

Lanes A-D are authorized to begin from the frozen base commit. Material contract changes require a
manifest amendment approved by the owner.

## Outcome

Make live Houdini verification routine rather than artisanal. One local entry point must describe
and run explicitly selected verification tiers, emit deterministic hashed evidence summaries, use
small rebuildable fixtures, report useful current-build drift, and keep expensive or privileged
work gated. The cycle designs—but does not activate—a self-hosted Houdini runner.

## Required integrated deliverables

1. `scripts/run_acceptance.py` with explicit tier selection for:
   `pure`, `hython-read`, `graph-edit`, `single-frame`, `frame-range`, `pdg-child`, `simulation`,
   `viewport`, and `karma`.
2. Versioned acceptance request/result schemas and deterministic SHA-256 summary behavior.
3. Summaries containing build, license, package inventory, exact command, duration, budgets,
   artifacts, and `pass|warn|pending|blocked|not_applicable` states.
4. Small fixture builders whose source of truth is Python/recipes; no committed `.hipnc` binaries.
5. Baseline and compatibility records for points, primitives, memory, cook time, cache bytes,
   frames, resolution, operator availability, and parameter signatures.
6. A locked-down self-hosted runner threat model and operations design with activation explicitly
   disabled pending separate human approval.
7. A release evidence matrix that never collapses pure, Hython, interactive, plugin, render,
   local-model, external-model, or human-review gates.

## Non-goals

- No self-hosted runner registration, GitHub secret creation, workflow activation, or license
  automation.
- No Horizon 3 project compiler or new creative vertical.
- No plugin installation or global Houdini/package configuration change.
- No large simulation, long frame range, or render above Apprentice limits.
- No arbitrary graph builder, unrestricted VEX/Python execution, or weakening of policy gates.
- No package version bump, release tag, changelog, root README, registry, or workflow edit by a
  parallel lane.

## Lane DAG

```text
                    G001-A acceptance core
                  /                         \
v0.30.0 baseline +-- G001-B Hython tiers ----+--> G001-I integration captain --> v0.35 gate
                  +-- G001-C probes/baselines+
                  \-- G001-D runner governance/
```

Lanes A-D are independent and start from the exact base commit. They do not consume one another's
branches. The integration captain starts only when all four receipts are `ready`, or when a
documented owner decision removes or defers a blocked lane.

## Ownership matrix

| Lane | Owned implementation paths | Owned tests/docs | Must not edit |
|---|---|---|---|
| A | `hermes_houdini/acceptance/{__init__,schema,runner}.py`, `scripts/run_acceptance.py` | `tests/unit/test_acceptance_{schema,runner}.py`, `docs/grinder/receipts/G001-A.md` | Hython adapters, probes, shared metadata |
| B | `hermes_houdini/acceptance/{fixtures,hython_tiers}.py` | `tests/hython/test_acceptance_tiers.py`, `tests/fixtures/acceptance/README.md`, `docs/grinder/receipts/G001-B.md` | entry CLI, schemas, probes, shared metadata |
| C | `hermes_houdini/acceptance/{baselines,compatibility}.py` | `tests/unit/test_acceptance_{baselines,compatibility}.py`, `tests/hython/test_acceptance_probes.py`, `docs/acceptance-baselines.md`, `docs/grinder/receipts/G001-C.md` | entry CLI, fixtures, shared metadata |
| D | none | `docs/security/SELF_HOSTED_HOUDINI_RUNNER_THREAT_MODEL.md`, `docs/acceptance/{OPERATIONS,RELEASE_EVIDENCE_MATRIX}.md`, `docs/grinder/receipts/G001-D.md` | all code and workflows |
| I | all integration seams | shared metadata, exports, docs, release evidence | changing lane history or inventing missing evidence |

Paths in braces are exact filenames, not directory ownership. New files outside the table require
a manifest amendment. Existing files are read-only to lanes A-D even when located in a listed
directory.

## Frozen cross-lane contract

The integration captain will reconcile imports. Parallel lanes must use these concepts:

- schema ID: `hermes.houdini.acceptance.v1`;
- tier IDs exactly as listed under deliverable 1;
- evidence states: `pass`, `warn`, `pending`, `blocked`, `not_applicable`;
- each tier has `tier`, `status`, `command`, `started_at`, `duration_seconds`, `budget`,
  `observed`, `artifacts`, `warnings`, and `errors`;
- overall status is mechanical: `blocked` if any required tier blocks, `pending` if a required
  tier was not run, `warn` if no required tier blocks/pends but a warning exists, else `pass`;
- canonical JSON is UTF-8, sorted keys, compact separators, no NaN/Infinity; the summary hash is
  SHA-256 of the canonical payload excluding its own `summary_sha256` field;
- no tier auto-grants an approval or interprets human taste;
- Houdini imports are lazy and absent from pure import paths.

Lane A may define richer typed structures without contradicting this minimum. Lanes B and C return
plain mappings compatible with it; integration adapts them rather than having lanes import sibling
branches.

## Baseline and expected commands

From the clean base repository:

```bash
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython \
  -m pytest tests/hython -o addopts='' -q
```

Recorded v0.30 baseline: `168 passed, 4 skipped` pure and `34 passed` Hython. Every lane must record
its observed baseline; a mismatch is investigated and written into the receipt rather than hidden.
In a restricted Codex shell, Hython may incorrectly report that Qt requires the `neon` CPU feature;
rerun the exact Hython command with normal sandbox escalation so the native process can inspect the
host CPU. Do not work around this by replacing Houdini binaries or changing global configuration.

## Integration order

1. Create `codex/grinder-g001-integration` at the exact base SHA.
2. Integrate A, then B, then C, then D with ordinary merge commits or reviewed cherry-picks whose
   source commits remain identifiable.
3. Reconcile only the declared seams: package imports, CLI adapter registration, tier composition,
   docs navigation, release metadata, and test discovery.
4. Run pure and lint gates.
5. Run Hython tiers from an unused disposable artifact root.
6. Run bounded viewport/Karma proof only with the declared approval and budget.
7. Produce the integrated evidence matrix and release notes. Human review remains pending unless a
   human actually records it.
8. Open a PR to protected `main`; never force-push or bypass required checks.

## Cycle exit gate

G001 is `VERIFIED` only when:

- all required pure and Hython tests pass on the integrated head;
- the one-entry acceptance CLI proves tier selection, dry planning, and deterministic hashing;
- current-build probes produce actionable diffs on a deliberately mismatched fixture;
- at least one small graph-edit/single-frame fixture passes in Apprentice 22.0.368;
- viewport and Karma tiers are either authentically passed under budget or explicitly pending;
- the runner remains disabled and its threat model has a separate approval boundary;
- every lane receipt and the integrated matrix report exact evidence without inferred gates;
- final protected-branch CI passes.
