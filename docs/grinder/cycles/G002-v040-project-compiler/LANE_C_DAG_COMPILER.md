# Grinder Lane G002-C — Deterministic DAG Compiler

## Mission

Implement the pure compiler kernel that resolves an already normalized project mapping, capability
catalog, and adapter records into a deterministic, reviewable execution plan. The compiler proves
dependency/contract/resource coherence only. It never loads YAML, imports sibling lanes, mutates a
graph, cooks, chooses a creative winner, or automatically executes its output.

## Frozen execution contract

- Cycle state at dispatch: `ACCEPTED`
- Repository: `mlflautt/Houdini-Lab`
- Local root: `/Users/m1/houdini-g002-c`
- Base tag/commit: exact accepted values from `CYCLE_MANIFEST.md`
- Branch: `codex/grinder-g002-c-dag-compiler`
- Runtime: pure Python; H22.0.368 regression only
- License baseline: Houdini Apprentice non-commercial
- Depends on other lanes: none; use inline mappings matching the frozen manifest
- Merge authority: integration captain only

## Read before editing

Read `AGENTS.md`, architecture, Horizon 3, G002 manifest/this brief,
`hermes_houdini/{capabilities.py,handoff.py,graph_batch.py,execution.py}` and
`schemas/control_plane.py`. Existing execution code is read-only reference: do not make the plan
call it. Do not read or import unmerged Lane A/B implementations.

## Startup preflight

Run root/clean/base/remote, `gh`/SSH, full pure, and Ruff checks. Stop on any placeholder/wrong base or if an
existing public planner already conflicts with the frozen schema; report the conflict.

## Owned paths

- `hermes_houdini/project_compiler.py`
- `tests/unit/test_project_compiler.py`
- `docs/project-compiler.md`
- `docs/grinder/receipts/G002-C.md`

Do not edit spec/adapters/observer, execution, graph batch, schemas, exports, CLI, examples, package
metadata, root docs, workflows, or another receipt.

## Required API and plan contract

Expose pure behavior equivalent to:

```text
compile_project(spec: Mapping, *, capability_catalog: Mapping,
                adapter_records: Iterable[Mapping]) -> dict
```

Inputs are trusted only as JSON-shaped mappings, not as instances of sibling types. Validate the
frozen fields needed to compile and return structured blockers rather than tracebacks for project
contract failures. Programmer type errors may raise `ValueError` with deterministic paths.

Output schema `hermes.houdini.project_plan.v1` includes:

- exact spec/catalog/adapter hashes and compatibility identity;
- deterministic stage IDs derived from project/instance/variant, never random UUIDs;
- stable topological stage order and explicit edges;
- exact capability ID/version/context plus named parent/output contracts;
- explicit contract bindings and selected exact adapter record;
- graph-edit/cook/cache/render scope, checkpoint boundary, budget, risk, approvals, and evidence;
- variants and human decisions preserved in source order with null ownership fields;
- aggregate budgets and structured blockers/warnings;
- `automatic_execution: false`, `automatic_ranking: false`, and `winner: null`;
- canonical `plan_sha256` excluding only its own hash.

Compilation blocks missing/ambiguous exact capabilities or adapters, dependency cycles, undeclared
ports/contracts, context/build/license mismatch, aggregate or stage budget overflow, unavailable
dependency without an explicitly permitted native fallback, and an output that has multiple
unresolved providers. Never resolve by latest version, list order, or plugin preference.

Successful plans may contain `pending` evidence/approval stages; they are dry plans, not green live
results. Keep checkpoints before coherent mutation stages and expensive cook/render stages. Do not
emit raw Python, VEX, arbitrary node operations, or shell commands.

## Implementation sequence

1. Build inline valid and failure mappings independent of A/B modules.
2. Implement exact capability and contract indexes, deterministic topological sort, adapter
   resolution, budget aggregation, and canonical hash.
3. Add tests for key-order/repeated-process stability, disconnected/cyclic graphs, duplicate
   providers, missing adapters, build/license/dependency drift, budget overflow, variants, and
   preservation of pending approvals/human slots.
4. Document plan review and why compilation cannot grant execution.
5. Run full gates and commit the receipt.

## Acceptance gates

```bash
.venv/bin/python -m pytest tests/unit/test_project_compiler.py -o addopts='' -q
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
git diff --check
git diff --name-only <BASE_SHA>...HEAD
```

All pure gates pass. Hython/graph/cook/render/model/human evidence is `not_applicable`.

## Receipt and handoff

Commit `G002-C.md`, push, and open a component PR. Report the exact plan schema/API, deterministic
hash proof, deliberate blocker coverage, tests, scope, deviations, and integration assumptions.
Do not merge.

## Stop conditions and non-goals

Stop before importing a sibling lane, adding YAML/file discovery, calling runtime code, inventing an
adapter, weakening exact versions, or filling human fields. Execution/resume belongs after G002 and
requires a future explicit policy surface.
