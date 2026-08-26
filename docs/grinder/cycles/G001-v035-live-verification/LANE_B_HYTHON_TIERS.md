# Grinder Lane G001-B — Hython Tiers and Rebuildable Fixtures

## Mission

Implement bounded Houdini-side tier adapters and tiny rebuildable fixtures for read-only, graph
edit, single-frame, frame-range, PDG-child, simulation, viewport, and Karma evidence. This lane
proves Houdini mechanics without owning the unified CLI or pure schema.

## Frozen execution contract

- Cycle state at dispatch: `ACCEPTED`
- Repository/base: `mlflautt/Houdini-Lab`, `v0.30.0`,
  `b8b8f4c4b702b4f895bbee3098c90006541a7373`
- Branch: `codex/grinder-g001-b-hython-tiers`
- Houdini: Apprentice `22.0.368`
- Hython: `/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython`
- License/output: non-commercial `.hipnc`, Karma CPU, at most `1280x720`
- Depends on other lanes: none; return manifest-compatible plain mappings
- Merge authority: integration captain only

## Read before editing

Read `AGENTS.md`, `docs/architecture.md`, Horizon 2 of the grand plan, the v0.30 runbook, accepted
manifest, this brief, `hermes_houdini/resource_control.py`, cook/observation/PDG/simulation tools,
representative `scripts/run_sprint*_acceptance.py` files, and existing Hython fixtures/tests. Treat
all except owned paths as read-only.

Before writing HOM, inspect the installed build's operator/parameter APIs using read-only Hython or
official versioned SideFX docs. Record the source in the receipt. Do not copy a tutorial into a
monolithic script.

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
/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython -m pytest tests/hython -o addopts='' -q
```

GitHub's successful SSH greeting exits nonzero because it offers no shell; record the greeting.
Network checks and the native Hython process may require normal sandbox escalation.

If `.venv/bin/python` is absent, use `python3 -m venv .venv` followed by
`.venv/bin/python -m pip install -e '.[dev]'`; dependency download requires normal user approval.
Do not mutate the Houdini installation or globally install packages. Existing Hython test
infrastructure should run without injecting PyYAML. Record pure, Ruff, and Hython baselines before
editing. If a restricted Codex shell reports that Qt requires the `neon` CPU feature, rerun the
exact Hython command with normal sandbox escalation; do not change the binary or host configuration.

## Owned paths

Only create/edit:

- `hermes_houdini/acceptance/fixtures.py`
- `hermes_houdini/acceptance/hython_tiers.py`
- `tests/hython/test_acceptance_tiers.py`
- `tests/fixtures/acceptance/README.md`
- `docs/grinder/receipts/G001-B.md`

Do not create `hermes_houdini/acceptance/__init__.py`; Git can carry the two module files until
integration. Do not edit the unified CLI, schemas, probes, workflows, exports, or release metadata.

## Fixture and tier contracts

- Fixtures are source-built in a caller-supplied unused absolute artifact root. Never commit
  `.hipnc` or generated pixels/caches.
- Every managed node has `hermes_id`, `hermes_role`, and `hermes_created_by`; all node paths are
  absolute and no selection/pane/display/frame state is assumed.
- Graph edits are wrapped in an undo group and use named Null output contracts.
- Each tier accepts explicit budgets and returns a plain mapping matching the manifest. It neither
  imports Lane A nor writes the final summary.
- Read-only does not cook. Graph-edit builds but does not force a display-chain cook. Single-frame,
  frame-range, PDG child, simulation, viewport, and Karma remain distinct calls.
- Default test fixtures stay tiny: at most 10k points, 8 frames, 256 MB estimated memory, 256 MB
  artifact bytes, `640x360` viewport/render, 16 Karma samples, and 120 seconds per expensive tier.
- PDG child execution requires the existing external-process policy approval. Simulation and render
  adapters refuse missing explicit authorization; tests may verify refusal without running cost.
- Preserve/restores frame and relevant display/render state. Do not overwrite existing paths.
- Failures return actionable warnings/errors and partial artifact provenance; never manufacture a
  pass after a skipped cook/render.

## Implementation sequence

1. Probe exact H22.0.368 operator/parameter names read-only.
2. Build a minimal native SOP fixture and source builders for any additional tier fixtures.
3. Implement tier adapters from cheapest to most expensive, with explicit budget/refusal paths.
4. Test non-cooking/read-only behavior, stable IDs, graph readability, state restoration, output
   non-overwrite, and tier separation.
5. Run cheap tiers. Run simulation/viewport/Karma only in a disposable root and only under the
   frozen budgets; it is acceptable for expensive proof to remain `pending` in this lane if the
   tests rigorously validate gating. Integration owns the release proof.
6. Run all gates, receipt, commit, push, and open an unmerged PR.

## Acceptance gates

```bash
HYTHON=/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython
"$HYTHON" -m pytest tests/hython/test_acceptance_tiers.py -o addopts='' -q
"$HYTHON" -m pytest tests/hython -o addopts='' -q
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
git diff --name-only b8b8f4c4b702b4f895bbee3098c90006541a7373...HEAD
```

Targeted and full Hython, pure, Ruff, and scope gates must pass. Report each live evidence tier
separately; structural tests do not count as viewport/Karma proof.

## Receipt and handoff

Commit `docs/grinder/receipts/G001-B.md`, push, and open an unmerged component PR targeting `main`,
clearly titled `[G001-B]`. Include exact operator probe sources/results, fixture budgets,
branch/head/PR, changed files, commands/results, artifacts/hashes, per-tier evidence, deviations,
and the plain adapter call signatures for integration.

## Stop conditions and non-goals

Stop before plugin/global config changes, unclear operators, over-budget work, destructive paths,
arbitrary Python/VEX, or ownership conflict. Do not implement CLI/schema/hash logic, activate
runners, edit workflows, or claim visual evidence that was not authentically captured.
