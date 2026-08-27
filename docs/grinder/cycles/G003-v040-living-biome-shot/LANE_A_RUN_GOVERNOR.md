# Grinder Lane G003-A — Project Run Governor

## Mission

Implement the Houdini-independent run-state governor that converts one accepted G002 dry plan into
a fail-closed, resumable sequence of explicitly approved stages. It describes readiness and records
state; it never imports Houdini, invokes a tool, starts a process, discovers a scene, grants an
approval, or retries automatically.

## Frozen execution contract

- Local root: `/Users/m1/houdini-g003-a`
- Branch: `codex/grinder-g003-a-run-governor`
- Base: exact full SHA in `CYCLE_MANIFEST.md`
- Other-lane dependencies: none
- Merge authority: integration captain only

Stop if the manifest is not `ACCEPTED`, motion is `UNSET`, HEAD differs from the full base, or the
checkout is dirty. Read `AGENTS.md`, `docs/architecture.md`, the G002 compiler/observer/runtime
contracts, the accepted G003 manifest, and this brief before editing.

## Owned paths

- `hermes_houdini/project_runtime.py`
- `tests/unit/test_project_runtime.py`
- `docs/project-runtime.md`
- `docs/grinder/receipts/G003-A.md`

Do not edit recipes, skills, compiler, observer, project fixtures, shared metadata, CLI, workflows,
or another receipt.

## Required pure API

Expose equivalent plain-mapping behavior:

```text
prepare_project_run(plan, *, source_identity, runtime_identity, approvals=()) -> dict
next_runnable_stage(run_state, *, stage_records=()) -> dict | None
record_stage_result(run_state, record) -> dict
project_run_sha256(run_state) -> str
```

The schema is `hermes.houdini.project_run.v1`. Bind the exact plan hash and source identity; reject
dirty/ambiguous source, mismatched build/license/package/catalog/adapter identity, invalid or stale
approval subjects, duplicate stage records, dependency success inferred from absence, over-budget
results, and any stage not present in the plan. Preserve plan topological order.

States are explicit: `planned`, `awaiting_approval`, `ready`, `running`, `passed`, `warned`,
`blocked`, `cancelled`, `interrupted`. A stage becomes ready only when all dependencies passed,
required approval records exactly match action/hash/budget and remain valid, and no prior blocker
exists. `next_runnable_stage` returns at most one immutable description with checkpoint requirement,
risk, scope, ceilings, requested evidence, and `automatic_execution: false`.

Cancellation/interruption are terminal until an explicit new resume record references the prior run
hash. Never convert `pending`/missing evidence into pass. Keep human decisions null and outside the
mechanical state machine.

## Required tests

- stable hashes across ordering/fresh processes;
- exact stage progression and dependency stop;
- missing/stale/wrong-subject approval;
- source/build/license/package/catalog/adapter drift;
- duplicate/unknown/out-of-order stage result;
- over-budget and missing checkpoint;
- cancellation/interruption/resume lineage;
- no import of `hou`, subprocess, bridge client, or UI modules;
- no automatic execution/ranking/winner field can become true/non-null.

Run targeted/full pure tests, Ruff, diff check, and import in a clean Python process. Hython, graph,
cook, pixel, plugin, model, downstream, and human evidence are not applicable to this lane.

## Handoff

Commit only owned paths, create `G003-A.md` from actual results, push the branch, and open an
unmerged component PR. Report full base/head SHAs, public API, files, commands/results, deviations,
and integration notes. Stop rather than widening into execution or editing sibling contracts.
