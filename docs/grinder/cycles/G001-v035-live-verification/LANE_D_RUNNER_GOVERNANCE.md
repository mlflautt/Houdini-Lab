# Grinder Lane G001-D — Self-Hosted Runner Governance and Evidence Operations

## Mission

Produce an implementation-ready threat model and operating design for a future macOS/Houdini
self-hosted runner, plus the release evidence matrix and local acceptance operations guide. This is
a documentation-only lane. It must make activation safer to review without activating anything.

## Frozen execution contract

- Cycle state: `ACCEPTED`
- Base: `v0.30.0` at `b8b8f4c4b702b4f895bbee3098c90006541a7373`
- Branch: `codex/grinder-g001-d-runner-governance`
- Runner activation: forbidden in G001
- Network/GitHub mutation: not required; repository inspection is sufficient
- Depends on other lanes: none
- Merge authority: integration captain only

## Read before editing

Read `AGENTS.md`, `docs/architecture.md`, the complete Horizon 2 section, accepted manifest, this
brief, `.github/workflows/ci.yml`, `docs/apprentice-constraints.md`, `docs/bridge.md`,
`docs/resource-control.md`, `docs/local-vision-critic.md`, plugin governance docs, and the v0.30
release evidence. These are read-only.

Use authoritative GitHub and SideFX documentation only if local material cannot establish a
security or license fact. Record URLs/access dates and distinguish documented fact, inference, and
proposal. Do not change remote state.

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
sed -n '1,180p' .github/workflows/ci.yml
rg -n "if: false" .github/workflows/ci.yml
```

GitHub's successful SSH greeting exits nonzero because it offers no shell; record the greeting.
Network checks may require normal sandbox escalation.

If `.venv/bin/python` is absent, use `python3 -m venv .venv` followed by
`.venv/bin/python -m pip install -e '.[dev]'`; dependency download requires normal user approval.
Record full pure and Ruff baselines. Inspect—do not execute—current workflow permissions/triggers
and confirm the Hython job is disabled. No GitHub settings, secrets, labels, runners, or workflows
may be changed.

## Owned paths

Only create/edit:

- `docs/security/SELF_HOSTED_HOUDINI_RUNNER_THREAT_MODEL.md`
- `docs/acceptance/OPERATIONS.md`
- `docs/acceptance/RELEASE_EVIDENCE_MATRIX.md`
- `docs/grinder/receipts/G001-D.md`

No code or `.github/` path is owned.

## Threat-model contract

Cover at minimum:

- assets: repository integrity, artist files, SideFX credentials/license, GitHub token, SSH keys,
  package caches, rendered artifacts, user privacy, and host availability;
- trust boundaries: public/fork PR, collaborator PR, protected main, release/tag, GitHub service,
  runner process, Houdini licensing, bridge loopback, child processes, plugins, caches/artifacts;
- threats: untrusted PR code execution, persistence between jobs, credential exfiltration, symlink
  and path traversal, fork/secrets behavior, workflow mutation, poisoned caches/artifacts, plugin
  loading, broad `hou`/Python execution, network egress, denial of service, concurrent Houdini
  sessions, license exhaustion, stale processes, and user-session/UI interference;
- controls: dedicated least-privilege account/host, ephemeral workspace, outbound policy, no secrets
  on untrusted events, action pinning, allowlisted commands, time/memory/disk limits, concurrency 1,
  process-group termination, cache isolation, artifact retention, cleanup verification, audit logs,
  and a kill switch;
- explicit residual risks, owner, review cadence, incident/rollback procedure, and activation
  prerequisites;
- a separate human approval checkpoint after design review. G001 cannot satisfy it implicitly.

## Operations and evidence contracts

- Define local commands from clean checkout through pure/Hython/tiered acceptance, evidence hashing,
  artifact retention, and cleanup. Use placeholders where Lane A/B/C interfaces are not yet merged.
- The release matrix must include pure CI, Hython read, graph edit, cook, frame range, PDG child,
  simulation, viewport, Karma, plugins disabled/enabled, interactive bridge, local model, external
  model, human aesthetic review, and downstream-app review.
- Every cell uses the manifest's status vocabulary and contains provenance or a reason it is
  pending/not applicable. Never use one generic green check for the whole release.
- Define who can promote each evidence type and what is invalidated by code, fixture, Houdini build,
  package, plugin, license, or hardware drift.

## Implementation sequence

1. Inventory current local and GitHub workflow trust boundaries from repository files.
2. Write the threat model with abuse cases, controls, residual risk, and activation checklist.
3. Write local acceptance operations/cleanup/incident procedures.
4. Write a reusable blank release matrix plus a G001/v0.35 interpretation section.
5. Check all relative links and claims, run pure/lint regression gates, receipt, commit, push, PR.

## Acceptance gates

```bash
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
rg -n "if: false" .github/workflows/ci.yml
git diff --name-only b8b8f4c4b702b4f895bbee3098c90006541a7373...HEAD
git diff --check
```

Pure, Ruff, disabled-runner check, clean diff, and scope gates must pass. Hython and visual evidence
are `not_applicable` to this documentation lane.

## Receipt and handoff

Commit `docs/grinder/receipts/G001-D.md`; push and open an unmerged component PR targeting `main`,
clearly titled `[G001-D]`. Report branch/head/PR, changed files, exact checks, sourced facts versus
proposals, residual risks, activation blockers, deviations, and integration placeholders needing
reconciliation.

## Stop conditions and non-goals

Stop before runner registration, workflow/secret/settings changes, license automation, downloads,
plugin install, or any remote mutation. Do not turn design recommendations into claims about
GitHub/SideFX behavior without a source or explicit inference label.
