# Project observer and drift index

`hermes_houdini.project_observer` builds one deterministic, Houdini-independent view of a
normalized project, its dry compiler plan, and only the evidence explicitly supplied by a caller.
It does not scan an artist scene, search a project directory, run a process, import `hou`, repair an
artifact, execute a plan, call a model, or infer a human choice.

## API

```python
from hermes_houdini.project_observer import build_project_index

index = build_project_index(
    project,
    plan,
    project_root="/absolute/approved/project",  # optional
    runtime_identity=current_identity,          # optional
    execution_records=records,
    artifacts=artifacts,
)
```

```text
build_project_index(project: Mapping, plan: Mapping, *,
                    project_root: str | Path | None = None,
                    runtime_identity: Mapping | None = None,
                    execution_records: Iterable[Mapping] = (),
                    artifacts: Iterable[Mapping] = ()) -> dict
```

The project and plan must identify `hermes.houdini.project.v1` and
`hermes.houdini.project_plan.v1`. The observer consumes plain JSON-shaped mappings and imports no
G002 sibling implementation. A supplied `topological_order` must name every stage exactly once and
becomes the index stage order; otherwise the existing plan stage order is retained. Variant order is
always retained.

## Index contract

The result schema is `hermes.houdini.project_index.v1`. Its principal fields are:

- `source_sha256`, `plan_sha256`, and `index_sha256`; the index hash is canonical SHA-256 and
  excludes only `index_sha256` itself;
- ordered `variants` and `stages`, with each stage's original dry-plan fields, order, attached valid
  execution record, independent evidence rows, approvals, and mechanical execution status;
- `contracts.producers` and `contracts.consumers`, plus checkpoints and explicit artifacts;
- `evidence_by_rung`, which never collapses graph, data, pixel, plugin, model, human, or downstream
  evidence into one value;
- pending approvals, human decision slots, append-only explicit human records, warnings, blockers,
  rejected lineage, and structured compatibility/artifact drift;
- separate `mechanical_status` and `human_status` values;
- `automatic_execution: false`, `automatic_ranking: false`, and a null `winner` unless an explicit
  human record supplies one.

Input mappings are converted to finite JSON values. Invalid schemas, non-finite numbers, malformed
stage orders, duplicate plan stage IDs, or non-null human-owned fields in the dry project/plan raise
`ValueError`. Runtime/evidence problems that belong in an observation—unknown or duplicate records,
record hash mismatches, runtime drift, and artifact-integrity failures—become structured blockers.

## Execution and evidence records

Every record requires `stage_id` (or `id`) naming one declared stage. A normal record can contain:

```json
{
  "stage_id": "terrain",
  "source_sha256": "<normalized project hash>",
  "plan_sha256": "<dry plan hash>",
  "status": "pass",
  "evidence": [
    {"rung": "graph", "status": "pass", "report_sha256": "<hash>"},
    {"rung": "data", "status": "pass", "report_sha256": "<hash>"}
  ],
  "artifacts": [],
  "human": null
}
```

The five allowed G001 evidence states are `pass`, `warn`, `pending`, `blocked`, and
`not_applicable`. Missing execution for a planned stage is `pending`. Required evidence that is
reported `not_applicable` remains mechanically pending unless the stage itself was declared
non-applicable with a concrete `non_applicable_reason`. Evidence supplied for an undeclared rung is
retained but does not silently make that rung required.

Unknown stages, multiple records for one stage, and claimed `source_sha256`, `project_sha256`, or
`plan_sha256` values that do not match the observed inputs are blockers. A duplicate record is not
chosen by list order: neither duplicate becomes the stage's accepted execution record.

An optional `human` mapping on a valid stage-bound record is the only source for rating, winner,
feedback, or continuation values. Planned variant and decision fields must remain null. The index
copies human records as append-only provenance and leaves the dry variants unchanged, so prior
pending or rejected lineage is not rewritten.

## Mechanical and human status

Mechanical aggregation follows the G001 order:

1. any structured blocker gives `blocked`;
2. otherwise missing required execution/evidence, runtime identity, or approval gives `pending`;
3. otherwise an applicable warning gives `warn`;
4. otherwise completed applicable evidence gives `pass`;
5. a completely inapplicable surface gives `not_applicable`.

`human_status` is computed separately. Declared human decisions with no explicit human record stay
`pending`; no decisions gives `not_applicable`; supplied records retain their own five-state result.
Mechanical success can never promote human status or choose a creative winner.

## Drift categories

The `drift` list always addresses these categories independently:

| Category | Comparison |
|---|---|
| `houdini_build` | exact planned build versus supplied current build |
| `license` | exact license mode |
| `package` | exact package identity/version mapping or scalar |
| `optional_dependency` | every declared dependency must be present; extra current dependencies are allowed |
| `capability_adapter_identity` | exact normalized capability/adapter identities, independent of input ordering |
| `source_hash` | current source/project hash versus normalized project hash |
| `artifact_integrity` | only explicit path/hash verification results |

Expected capability identities are taken from plan stages and explicit adapters when the plan does
not already provide a consolidated identity. Missing runtime identity is `pending`; an exact match is
`match`; an incompatibility is `drift` and creates a structured blocker. A category the plan does
not claim is `not_applicable`. Artifact bytes left unverified are `not_checked`, not green.

## Artifact path and hash policy

Artifacts come only from the `artifacts` argument or a supplied execution record. The observer never
walks a directory.

- Without `project_root`, artifact mappings are preserved and `integrity.status` is `not_checked`.
  No artifact path is opened, resolved, stated, or discovered.
- With a separately supplied absolute `project_root`, every artifact path must be absolute and
  lexically confined beneath it. The default still performs no byte read.
- `durable: true` requires a valid SHA-256 claim.
- `verify: true` is the explicit opt-in to resolve the root and file, reject a symlink escape,
  confirm it is a file, compute SHA-256, and record size. A missing file, missing claimed hash, or
  hash mismatch is a blocker.

Callers should supply stable project-relative meaning in artifact metadata even though the verified
path is absolute. Paths and hashes are evidence inputs; the observer never creates or repairs them.

## Determinism

Canonical JSON sorts mapping keys and rejects NaN/Infinity. Execution records and explicit artifacts
are sorted by stable identity before joining; their caller input order cannot select a record or
change the index hash. Stage and variant ordering remains semantic and therefore remains in the hash.
Warnings, blockers, pending stages, non-applicable reasons, rejected alternatives, approvals, and
blank human fields also remain in the hash.

## G003 live-evidence seam

G002 produces a dry immutable baseline. G003 should retain the normalized project and dry
`plan_sha256`, run separately authorized graph/cook/render operations, and append stage-bound
execution records plus explicit artifact mappings. It then calls `build_project_index` again with
the current runtime identity. It must not rewrite the dry plan, replace prior rejected/pending
lineage, manufacture pixel/model/human success from structural evidence, or ask the observer to scan
the live HIP. A later index is a new hashed observation over appended evidence, not a mutation that
turns the earlier dry index green.

This lane itself makes no Houdini, graph, cook, pixel, plugin, model, human-review, or downstream
runtime claim. Those acceptance rows are `not_applicable` to G002-D with that concrete reason; the
schema merely preserves future evidence without conflating it.
