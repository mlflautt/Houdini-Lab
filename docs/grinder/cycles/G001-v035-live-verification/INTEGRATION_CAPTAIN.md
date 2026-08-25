# Grinder Lane G001-I — Integration Captain

## Mission

Integrate the four accepted G001 lane heads into one coherent v0.35 candidate, reconcile only the
declared seams, run the union of evidence gates on the pinned Houdini build, and deliver one
protected-main PR with truthful release evidence. Do not begin until the planning package is merged,
the manifest is accepted, and A-D have receipts and immutable head SHAs.

## Inputs required before startup

- accepted `CYCLE_MANIFEST.md` and any approved amendments;
- lane A-D PR URLs, full head SHAs, and committed receipts;
- exact base `b8b8f4c4b702b4f895bbee3098c90006541a7373`;
- a clean `codex/grinder-g001-integration` worktree at that SHA;
- access to Hython Apprentice 22.0.368 for release gates;
- explicit approval before authentic viewport/Karma, external process, or publication work.

If a receipt is missing, `blocked`, has out-of-scope files, or does not match its PR head, stop and
return it to the lane owner. Do not integrate a chat-only patch.

## Read before editing

Read all governing architecture/roadmap/runbook files, the Grinder architecture, accepted manifest,
all four lane briefs and receipts, lane diffs, existing acceptance harnesses, packaging/version
metadata, CI, release template, and protected-branch requirements.

## Startup and intake audit

```bash
git rev-parse HEAD
git status --short --branch
git remote -v
git fetch origin --tags --prune
git tag --points-at b8b8f4c4b702b4f895bbee3098c90006541a7373
gh auth status --hostname github.com
ssh -T git@github.com
```

GitHub's successful SSH greeting exits nonzero because it offers no shell; record the greeting.
Network/native-Houdini commands may require normal sandbox escalation.

For each lane, verify its head and scope before integration:

```bash
git diff --name-only b8b8f4c4b702b4f895bbee3098c90006541a7373...<LANE_HEAD>
git show --stat --oneline <LANE_HEAD>
```

Record the four accepted head SHAs in the integration receipt/release notes.

## Integration authority and owned paths

The captain may edit lane files only to reconcile cross-lane contracts or fix integrated defects,
and must attribute material repairs in the integration receipt. The captain exclusively owns:

- `hermes_houdini/__init__.py` and package exports/initializers;
- CLI adapter registration and cross-lane wiring;
- `README.md`, `CHANGELOG.md`, roadmap status, release docs, and Grinder cycle status;
- `pyproject.toml` and `.github/workflows/*` if genuinely required (the Houdini runner remains
  disabled);
- integrated evidence artifacts intended for Git;
- `docs/grinder/receipts/G001-I.md`.

Do not rewrite lane history, force-push, delete evidence lineage, activate a self-hosted runner, or
silently relax tests/policies/budgets.

## Integration sequence

1. Integrate A, B, C, D in that order using identifiable ordinary commits.
2. Run pure tests/Ruff after each integration; isolate regressions to the introducing lane.
3. Reconcile namespace initialization, CLI adapter discovery, result normalization, and docs links.
4. Add integration tests for the unified CLI plan and selected cheap Hython tiers. Avoid duplicating
   lane unit coverage.
5. Run `scripts/run_acceptance.py` from a new absolute disposable artifact root. Exercise tiers
   individually so their approvals, costs, and evidence stay distinct.
6. Run deliberate compatibility mismatch and deterministic-hash checks.
7. With explicit approval, capture at least the manifest's required small graph-edit/single-frame
   proof. Run viewport/Karma within budget when approved; otherwise record `pending`, not `pass`.
8. Populate the release matrix from actual commands/artifacts. Keep human review pending unless the
   owner performs it.
9. Update version/release metadata consistently, but tag/release only after protected-main merge and
   final-main CI.
10. Write receipt, push, open the integration PR, resolve review, merge through protection, verify
    final-main CI, then publish only if authorized.

## Required integrated gates

At minimum:

```bash
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
.venv/bin/python scripts/run_acceptance.py --list-tiers
HYTHON=/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython
"$HYTHON" -m pytest tests/hython -o addopts='' -q
git diff --check
```

Also run the unified acceptance commands introduced by the lanes, deterministic hash repetition,
intentional compatibility mismatch, small graph/data proof, and any approved visual tiers. Record
exact commands, durations, budgets, absolute artifact paths, and SHA-256 values.

If a restricted Codex shell reports that Qt requires the `neon` CPU feature, rerun the exact
Hython command with normal sandbox escalation. Do not replace binaries or change host-wide
configuration to evade the sandbox symptom.

## Release decision

Technical gates may establish `VERIFIED`; they do not automatically establish `RELEASED`. Report:

- integrated branch/head and four source lane heads;
- PR and CI URLs;
- exact pure/Hython/tier results;
- each release-matrix status;
- real build/license/package inventory;
- artifacts and hashes;
- pending human/external/plugin/visual gates;
- any integration repair and its tests;
- whether merge/tag/release actions were actually performed.

Stop before any missing approval or if evidence contradicts a release claim.
