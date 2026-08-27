# Grinder Lane G003-D — Project Execution Receipt and Handoff

## Mission

Implement the pure, append-only evidence object that binds a G003 run to exact source, dry plan,
run state, runtime identity, stage results, live artifact bytes, approvals, and unresolved human
decisions. It reports truth; it performs no execution, discovery, aesthetic scoring, or file write.

## Frozen execution contract

- Local root: `/Users/m1/houdini-g003-d`
- Branch: `codex/grinder-g003-d-run-receipt`
- Base: exact accepted SHA in `CYCLE_MANIFEST.md`
- Other-lane dependencies: none; plain mappings only
- Merge authority: integration captain only

Stop unless manifest/base/cleanliness are exact. Read architecture, G002 observer/index, handoff and
acceptance schemas, provenance/path policy, the G003 manifest, and this brief.

## Owned paths

- `hermes_houdini/project_run_receipt.py`
- `tests/unit/test_project_run_receipt.py`
- `docs/project-run-receipt.md`
- `docs/grinder/receipts/G003-D.md`

Do not edit runtime governor, compiler/observer/handoff, recipes, skills, projects, shared metadata,
workflows, or another receipt.

## Required pure API

Expose equivalent semantics:

```text
build_project_run_receipt(project, plan, run_state, *, source_identity, runtime_identity,
                          stage_records=(), artifacts=(), human_records=()) -> dict
validate_project_run_receipt(receipt, *, project_root=None, verify_artifacts=False) -> dict
project_run_receipt_sha256(receipt) -> str
portable_project_handoff(receipt, *, project_root) -> dict
```

Schema `hermes.houdini.project_run_receipt.v1` binds exact hashes and stage identities. Durable
artifacts require verified live-byte SHA-256, size, portable project-relative path, producer stage,
and evidence rung. Symlink/traversal/outside-root paths block. Runtime drift, dirty/ambiguous source,
stage gaps/duplicates, stale checkpoint, plan/run mismatch, over-budget record, or claimed evidence
without a bound artifact block continuation.

Mechanical and human evidence aggregate separately. Missing execution is pending; an unavailable
optional gate is not applicable only with a concrete reason. Human records must be explicit,
append-only, exact-candidate-bound, and preserve verbatim feedback; absent records leave every
rating/selection/winner null. No technical metric becomes an aesthetic score.

## Required tests

Cover stable hashes, shuffled inputs, exact identity binding, stage gaps/duplicates, budget drift,
artifact live-byte pass/mismatch/missing/symlink escape, portable handoff across roots, pending rung
aggregation, immutable feedback text/candidate identity, rejected lineage, and refusal to prefill
human decisions. Clean import must not load Houdini or enumerate files.

Run targeted/full pure, Ruff, diff and ownership checks. Hython/live/pixel/model/downstream/human
review are not applicable to this implementation lane.

## Handoff

Commit only owned paths and the factual `G003-D.md`; push and open an unmerged component PR. Report
the API, exact gate results, hashes/fixtures, deviations, and integration requirements. Stop before
writing artifacts or changing the G002 observer to fit this module.
