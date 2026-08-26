# Grinder Lane G001-A — Acceptance Core and Unified CLI

## Mission

Build the pure-Python acceptance data model, deterministic summary hashing, tier planning logic,
and the single `scripts/run_acceptance.py` command surface. This lane defines orchestration
semantics but does not implement or claim live Houdini execution.

## Frozen execution contract

- Cycle state at dispatch: `ACCEPTED`
- Repository: `mlflautt/Houdini-Lab`
- Expected local root: a clean isolated clone/worktree of `/Users/m1/Houdini Lab`
- Base tag/commit: `v0.30.0` / `b8b8f4c4b702b4f895bbee3098c90006541a7373`
- Branch: `codex/grinder-g001-a-acceptance-core`
- Runtime contract: Python `>=3.11`; pure imports must work without Houdini
- Depends on other lanes: none
- Merge authority: integration captain only

Stop if the starting HEAD, clean state, repository identity, or accepted manifest differs.

## Read before editing

Read completely: `AGENTS.md`, `docs/architecture.md`, Horizon 2 in
`docs/HERMES_HOUDINI_GRAND_PLAN.md`, `docs/HERMES_V030_OPERATOR_RUNBOOK.md`, the accepted G001
manifest, this brief, `pyproject.toml`, `scripts/run_v030_acceptance.py`,
`hermes_houdini/schemas/result.py`, and `hermes_houdini/resource_control.py`. These are read-only
unless listed below.

## Startup preflight

```bash
git rev-parse --show-toplevel
git status --short --branch
git rev-parse HEAD
git remote -v
git tag --points-at HEAD
gh auth status --hostname github.com
ssh -T git@github.com
```

GitHub's successful SSH greeting still exits nonzero because it offers no shell; record the
greeting, not that expected exit code, as the authentication result. Network checks may require
normal sandbox escalation.

If `.venv/bin/python` is absent, create a repository-local environment and install the development
extra; network access requires normal user approval:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Record the baseline pure and lint results before editing.

## Owned paths

Only create/edit:

- `hermes_houdini/acceptance/__init__.py`
- `hermes_houdini/acceptance/schema.py`
- `hermes_houdini/acceptance/runner.py`
- `scripts/run_acceptance.py`
- `tests/unit/test_acceptance_schema.py`
- `tests/unit/test_acceptance_runner.py`
- `docs/grinder/receipts/G001-A.md`

Do not edit package version/exports, root docs, roadmap, workflows, other acceptance modules, or
existing tests. The integration captain owns import/export and runtime adapter reconciliation.

## Required contracts

- Implement schema `hermes.houdini.acceptance.v1` and the frozen tier/status/hash contract from the
  manifest.
- Validate duplicate/unknown tiers, invalid budgets, unsafe artifact roots, malformed results, and
  non-finite numeric values with useful errors.
- Separate request/plan from execution. `--plan` or equivalent must never import `hou`, cook, render,
  spawn a child process, or create an artifact directory.
- Default invocation must be safe: print help or a non-executing plan. Expensive tiers are never
  selected implicitly.
- Allow one or more explicit `--tier` values and an explicit absolute artifact root for execution.
- Keep wall-clock timestamps/durations outside the canonical hash input or normalize them so two
  semantically identical fixtures hash identically. Test the chosen rule.
- Provide a narrow adapter protocol the integration captain can use to register B/C tier runners
  without changing schemas.
- Never auto-grant approvals or convert absent visual/human evidence into `pass`.

## Implementation sequence

1. Write schema and hash tests first, including key-order invariance and self-hash exclusion.
2. Implement immutable or carefully validated pure data structures and canonical serialization.
3. Implement tier selection, required-tier aggregation, timeout/error mapping, and adapter protocol.
4. Implement the CLI with `--list-tiers`, non-executing planning, explicit execution, and JSON output.
5. Add focused CLI tests using fakes; never import Houdini in unit tests.
6. Run gates, inspect the scope diff, write the receipt, commit, push, and open an unmerged PR.

## Acceptance gates

```bash
.venv/bin/python -m pytest tests/unit/test_acceptance_schema.py tests/unit/test_acceptance_runner.py -o addopts='' -q
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
.venv/bin/python scripts/run_acceptance.py --list-tiers
.venv/bin/python scripts/run_acceptance.py --plan --tier pure --artifact-root /private/tmp/hermes-g001-a-plan
git diff --name-only b8b8f4c4b702b4f895bbee3098c90006541a7373...HEAD
```

All commands above must pass. Hython/visual gates are `not_applicable` because this lane makes no
live Houdini claim.

## Receipt and handoff

Commit `docs/grinder/receipts/G001-A.md` using the receipt template. Push the branch and open a
component PR targeting `main`, clearly titled `[G001-A]`; do not merge it. Final response: branch,
full head SHA, PR URL, exact changed files, test/lint/CLI results, evidence states, deviations,
blockers, and the adapter seam the captain must wire.

## Stop conditions and non-goals

Stop on an ownership conflict, baseline mismatch, need for Houdini imports in pure modules, global
install, network dependency, or architecture contradiction. Do not execute Houdini, implement
fixtures/probes, edit CI, bump versions, or redesign the v0.30 harness.
