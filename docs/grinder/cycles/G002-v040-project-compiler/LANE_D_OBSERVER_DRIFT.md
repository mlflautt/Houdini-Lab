# Grinder Lane G002-D — Project Observer and Drift Index

## Mission

Implement a Houdini-independent observer that combines an already normalized project, dry plan,
optional execution records, artifacts, and current runtime identity into one deterministic project
index. It reports what is planned, evidenced, missing, incompatible, or still human-owned without
scanning an artist scene or promoting absence to success.

## Frozen execution contract

- Cycle state at dispatch: `ACCEPTED`
- Repository: `mlflautt/Houdini-Lab`
- Local root: `/Users/m1/houdini-g002-d`
- Base tag/commit: exact accepted values from `CYCLE_MANIFEST.md`
- Branch: `codex/grinder-g002-d-observer-drift`
- Runtime: pure Python; H22.0.368 regression only
- License baseline: Houdini Apprentice non-commercial
- Depends on other lanes: none; use inline frozen mappings
- Merge authority: integration captain only

## Read before editing

Read `AGENTS.md`, architecture verification/handoff sections, Horizon 3, G002 manifest/this brief,
`hermes_houdini/{observation.py,evidence.py,handoff.py,acceptance/schema.py}` where present, and the
v0.35 release evidence matrix. These are read-only; do not import `hou` or reuse a live observer as
a hidden dependency.

## Startup preflight

Run identity/clean/base/remote, `gh`/SSH, pure baseline, and Ruff. Stop on placeholder/wrong base or a required
schema conflict rather than editing shared evidence contracts.

## Owned paths

- `hermes_houdini/project_observer.py`
- `tests/unit/test_project_observer.py`
- `docs/project-observer.md`
- `docs/grinder/receipts/G002-D.md`

Do not edit spec/adapters/compiler, current live observation/evidence/handoff modules, exports, CLI,
examples, package/root metadata, workflows, or another receipt.

## Required API and index contract

Expose pure behavior equivalent to:

```text
build_project_index(project: Mapping, plan: Mapping, *,
                    project_root: str | Path | None = None,
                    runtime_identity: Mapping | None = None,
                    execution_records: Iterable[Mapping] = (),
                    artifacts: Iterable[Mapping] = ()) -> dict
```

Output `hermes.houdini.project_index.v1` includes source/plan hashes, ordered variants/stages,
contract producers/consumers, checkpoints, artifact paths/hashes, evidence by rung, approvals,
human decisions, warnings/blockers, and drift categories for Houdini build, license, package,
optional dependency, capability/adapter identity, source hash, and artifact integrity.

Every execution record binds to one declared stage and uses the five G001 evidence states. Unknown,
duplicate, or hash-mismatched records are structured blockers. Missing execution for a planned
stage is `pending`; a stage declared non-applicable retains its concrete reason. Graph/data/pixel,
plugin, model, human, and downstream statuses never collapse into one green value. Human rating,
winner, feedback, and continuation fields are copied only from explicitly supplied human records;
the default remains blank/null.

Artifacts must be explicit absolute paths beneath the separately supplied absolute `project_root`,
have SHA-256 when claimed durable, and never be discovered by walking directories. Without an
explicit root the observer preserves metadata but does not touch artifact paths.
The pure observer may verify a supplied existing file only when the caller explicitly requests it;
default index construction performs no file write, no network, no process, and no HOM/UI access.

Top-level `mechanical_status` follows required evidence mechanically; `human_status` is separate.
Canonical `index_sha256` excludes only itself and preserves rejected/pending lineage.

## Implementation sequence

1. Define inline dry-plan, partial-execution, full-mechanical, drifted-runtime, missing-artifact,
   and human-pending fixtures.
2. Implement deterministic joins and drift/evidence routing without sibling imports.
3. Test all five states, artifact confinement/hash mismatch, unknown stage, independent human
   status, input-order stability, and no hidden filesystem/Houdini discovery.
4. Document how G003 will append live evidence rather than rewriting the dry index.
5. Run full gates and write the receipt.

## Acceptance gates

```bash
.venv/bin/python -m pytest tests/unit/test_project_observer.py -o addopts='' -q
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
git diff --check
git diff --name-only <BASE_SHA>...HEAD
```

All pure gates pass. Live Houdini, pixels, plugins, models, human review, and downstream import are
`not_applicable` to this lane and must remain separate in the index.

## Receipt and handoff

Commit `G002-D.md`, push, and open the component PR. Report schema/API, drift categories, evidence
routing tests, hash/path proof, exact commands/results, scope, deviations, and integration seam.
Do not merge.

## Stop conditions and non-goals

Stop before adding `hou`, directory crawling, live node inspection, automatic artifact repair,
model critique, human inference, or execution. Do not modify existing evidence schemas to make the
join easier; integration can adapt plain mappings explicitly.
