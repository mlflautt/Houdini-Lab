# Grinder Lane G002-A — Project Specification

## Mission

Implement the Houdini-independent parser and validator for `hermes.houdini.project.v1`. It turns one
explicit YAML mapping into canonical JSON-shaped project intent while preserving paths, variants,
budgets, exact capability versions, evidence gates, and blank human decisions. It never discovers
capabilities, selects adapters, compiles stages, or touches Houdini.

## Frozen execution contract

- Cycle state at dispatch: `ACCEPTED`
- Repository: `mlflautt/Houdini-Lab`
- Local root: `/Users/m1/houdini-g002-a`
- Base tag/commit: use the exact non-placeholder values in `CYCLE_MANIFEST.md`
- Branch: `codex/grinder-g002-a-project-spec`
- Houdini: no new claim; full H22.0.368 regression only
- Depends on other lanes: none
- Merge authority: integration captain only

Stop if the manifest is not accepted, contains a placeholder, the checkout is dirty, or HEAD differs
from its full base SHA.

## Read before editing

Read, without editing: `AGENTS.md`, `docs/architecture.md`, Horizon 3 in the grand plan, the G002
manifest, this brief, `hermes_houdini/schemas/control_plane.py`, `hermes_houdini/handoff.py`,
`projects/template/project.toml`, and existing schema tests. Reuse canonical/path-safety doctrine;
do not couple the new schema to the legacy project TOML shape.

## Startup preflight

```bash
git rev-parse --show-toplevel
git status --short --branch
git rev-parse HEAD
git remote -v
gh auth status --hostname github.com
ssh -T git@github.com
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
```

GitHub's authenticated SSH greeting returns a non-shell exit; record the greeting as success.
If `.venv` is absent, create it locally and install `.[dev]`; network access remains separately
approved. Record the actual baseline rather than copying counts from the brief.

## Owned paths

- `hermes_houdini/project_spec.py`
- `tests/unit/test_project_spec.py`
- `tests/fixtures/projects/g002-*.yaml`
- `docs/project-specification.md`
- `docs/grinder/receipts/G002-A.md`

Do not edit exports, package metadata, adapters, compiler, observer, CLI, project examples, recipes,
skills, root docs, workflows, or another receipt.

## Required API and behavior

Expose pure functions with equivalent semantics:

```text
normalize_project_spec(value: Mapping, *, project_root: str | Path) -> dict
load_project_spec(path: str | Path, *, project_root: str | Path) -> dict
project_spec_sha256(normalized: Mapping) -> str
```

The normalized mapping follows the manifest exactly and is safe canonical JSON. Loading accepts a
caller-supplied explicit file only; it does not search directories. `project_root` is absolute.
Embedded roots/references/artifact paths remain relative, resolve beneath it without symlink/traversal
escape, and serialize in normalized relative form so machine-specific home paths do not enter hashes.

Require exact semantic versions, finite nonnegative budgets, fixed seeds, explicit timeline/fps,
unique instance/variant/contract/decision IDs, declared contexts, and stable input order. Preserve
reference order and three equal-status variants. Reject `automatic_ranking: true`, non-null winner,
human rating, or selected continuation. These fields remain null placeholders; future human records
are append-only and outside this lane.

Use `yaml.safe_load`; reject non-object roots, aliases producing unexpected types, unknown top-level
fields, and NaN/Infinity. Do not validate whether a capability or adapter actually exists—that is
the compiler boundary.

## Implementation sequence

1. Write malformed fixtures first: traversal, duplicate IDs, latest/unversioned capability, budget
   omission, frame inversion, non-finite number, automatic ranking, and prefilled human fields.
2. Implement normalization with small validators and deterministic error paths.
3. Add one valid three-variant fixture proving canonical hash stability across key ordering and
   absolute checkout locations.
4. Document every field, path rule, null human field, and failure mode.
5. Run targeted/full gates and write the receipt from actual evidence.

## Acceptance gates

```bash
.venv/bin/python -m pytest tests/unit/test_project_spec.py -o addopts='' -q
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
git diff --check
git diff --name-only <BASE_SHA>...HEAD
```

All targeted and pure gates must pass. Hython, graph, cook, visual, plugin, model, and human gates
are `not_applicable` because this lane makes no such claim.

## Receipt and handoff

Commit `docs/grinder/receipts/G002-A.md` with base/head, exact files, commands/results, fixture/hash
evidence, deviations, and integration notes. Push the ordinary branch and open a component PR to
`main`; do not merge. Final response: branch, full head SHA, PR URL, files, gate results, evidence
statuses, deviations/blockers, and the exact public API.

## Stop conditions and non-goals

Stop before widening fields to solve a compiler concern, editing a sibling path, accepting absolute
embedded paths, adding execution, or choosing a variant. Do not create JSON Schema tooling, Pydantic,
network references, project discovery, or compatibility lookups unless the manifest is amended.
