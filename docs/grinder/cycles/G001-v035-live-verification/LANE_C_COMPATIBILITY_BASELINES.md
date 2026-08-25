# Grinder Lane G001-C — Compatibility Probes and Performance Baselines

## Mission

Build pure comparison/reporting logic plus narrow Hython probes that explain build drift in exact
operator and parameter terms, and evaluate observations against declared resource baselines. This
lane reports compatibility and performance; it does not run the full acceptance workflow.

## Frozen execution contract

- Cycle state: `ACCEPTED`
- Base: `v0.30.0` at `b8b8f4c4b702b4f895bbee3098c90006541a7373`
- Branch: `codex/grinder-g001-c-compatibility-baselines`
- Runtime: pure Python `>=3.11` plus read-only Hython Apprentice `22.0.368`
- Depends on other lanes: none
- Merge authority: integration captain only

## Read before editing

Read the root instructions, architecture, grand-plan Horizon 2, accepted manifest, this brief,
`hermes_houdini/houdini_adapter.py`, catalog/build compatibility logic, resource-control schemas,
`scripts/probe_*.py`, and representative recipe/skill manifests. Existing files are read-only.

Before encoding any H22 operator expectation, retrieve it from the installed build using a
read-only probe or official versioned SideFX documentation and record provenance in the receipt.

## Startup preflight

Run:

```bash
git rev-parse --show-toplevel
git status --short --branch
git rev-parse HEAD
git remote -v
git tag --points-at HEAD
gh auth status --hostname github.com
ssh -T git@github.com
/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython --version
```

GitHub's successful SSH greeting exits nonzero because it offers no shell; record the greeting.
Network checks and the native Hython process may require normal sandbox escalation.

If `.venv/bin/python` is absent, use `python3 -m venv .venv` followed by
`.venv/bin/python -m pip install -e '.[dev]'`; dependency download requires normal user approval.
Then record full pure, Ruff, and Hython baselines before editing. Do not install into Houdini or
change package configuration. If a restricted Codex shell reports that Qt requires the `neon` CPU
feature, rerun the exact Hython command with normal sandbox escalation; do not modify Houdini.

## Owned paths

Only create/edit:

- `hermes_houdini/acceptance/baselines.py`
- `hermes_houdini/acceptance/compatibility.py`
- `tests/unit/test_acceptance_baselines.py`
- `tests/unit/test_acceptance_compatibility.py`
- `tests/hython/test_acceptance_probes.py`
- `docs/acceptance-baselines.md`
- `docs/grinder/receipts/G001-C.md`

Do not create package initializers or edit schemas, fixtures, CLI, registries, workflows, or shared
metadata.

## Required contracts

- A versioned pure baseline record covers points, primitives, peak/estimated memory, cook seconds,
  cache bytes, frames, width, height, render samples, and optional tolerances.
- Comparisons distinguish missing observation, within budget, warning threshold, hard budget
  violation, and invalid/non-finite data. They do not call Houdini or auto-approve overruns.
- Compatibility expectations include context/category, exact operator type, required parameters,
  optional parameters, and tested build range.
- Compatibility results name missing operators, missing/unexpected parameters, parameter type or
  default drift where safely observable, and exact live build/license. A boolean alone is
  insufficient.
- Hython probing is read-only: create no scene nodes, cook nothing, change no frame/UI state, and
  write only when an explicit output path is supplied.
- Pure code imports without `hou`; the Hython adapter uses a lazy import.
- Include a deliberately mismatched expectation test proving that the human-readable diff is
  actionable and deterministic.
- Return plain mappings compatible with the manifest so integration can attach results to tier
  evidence without importing Lane A during parallel work.

## Implementation sequence

1. Write pure baseline and diff tests, including boundary/non-finite/missing cases.
2. Implement normalized baseline evaluation and compatibility diffing.
3. Add the narrow read-only Hython introspection adapter.
4. Test at least one known built-in SOP operator plus one intentional mismatch on H22.0.368.
5. Document baseline versioning, calibration versus regression, machine variance, and truthful
   interpretation. Performance thresholds are safety/diagnostic gates, not aesthetic scores.
6. Run gates, receipt, commit, push, and open an unmerged PR.

## Acceptance gates

```bash
.venv/bin/python -m pytest tests/unit/test_acceptance_baselines.py tests/unit/test_acceptance_compatibility.py -o addopts='' -q
.venv/bin/python -m pytest tests/unit -o addopts='' -q
HYTHON=/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython
"$HYTHON" -m pytest tests/hython/test_acceptance_probes.py -o addopts='' -q
"$HYTHON" -m pytest tests/hython -o addopts='' -q
.venv/bin/python -m ruff check .
git diff --name-only b8b8f4c4b702b4f895bbee3098c90006541a7373...HEAD
```

All gates must pass. No graph/data/pixel claim is in scope; mark them `not_applicable`.

## Receipt and handoff

Commit `docs/grinder/receipts/G001-C.md`; push and open an unmerged component PR targeting `main`,
clearly titled `[G001-C]`. Report branch/head/PR, exact files and commands, H22 probe provenance,
intentional mismatch output, baseline semantics, adapter call signatures, deviations, and blockers.

## Stop conditions and non-goals

Stop on operator uncertainty that cannot be resolved read-only, ownership conflict, need for scene
edits/cooks, external dependencies, or global configuration. Do not benchmark large scenes, infer
artistic quality, implement fixture execution, or modify release/CI metadata.
