# Local Acceptance Operations

- Scope: operator guide from clean checkout through evidence retention and cleanup
- Runtime target: Houdini Apprentice 22.0.368 on Apple silicon macOS
- Activation effect: none; these commands do not register a runner or change GitHub settings
- Status vocabulary: `pass`, `warn`, `pending`, `blocked`, `not_applicable`

This runbook separates pure, Hython, interactive, render, model, plugin, and human evidence. Run
only tiers authorized for the current acceptance request. A lower rung never promotes an unrun
higher rung. The G001 integration reconciles the schema/runner, Hython adapters, compatibility
probes, baselines, and this operator surface behind `scripts/run_acceptance.py`.

## Roles and approval boundary

| Role | Authority |
|---|---|
| Operator | execute an already approved request, preserve logs/artifacts, stop on mismatch |
| Technical reviewer | promote mechanical pure/Hython/graph/data/runtime evidence after provenance review |
| Plugin owner | promote exact package disabled/enabled evidence; cannot certify untested nodes |
| Model reviewer | promote a calibrated model response as advisory evidence only |
| Human artist/reviewer | own aesthetic rating, feedback, winner, and continuation decision |
| Downstream-app owner | accept an artifact in the named target app/workflow |
| Release owner | decide release readiness from individual cells; cannot fabricate missing evidence |

Medium/high/external actions retain their normal exact-envelope approvals. Runner activation,
plugin installation, model download, network access, license automation, and publication require
separate approval and are not granted by this runbook.

## 1. Prepare a clean, immutable checkout

Record commands and complete output in the run log:

```bash
git rev-parse --show-toplevel
git status --short --branch
git rev-parse HEAD
git remote -v
git tag --points-at HEAD
git diff --check
```

Stop with `blocked` if the requested commit does not match, tracked changes exist, or an output root
already exists. Do not clean an artist worktree. Use a new clone/worktree and a new absolute
artifact root instead. Record macOS/architecture, Python, Houdini build/license, package inventory,
plugin state, fixture revision, and acceptance schema before the first test.

Create a disposable root outside the repository without reusing a prior path:

```bash
ACCEPTANCE_RUN="$(mktemp -d /private/tmp/hermes-v035-acceptance.XXXXXX)"
ACCEPTANCE_ROOT="$ACCEPTANCE_RUN/artifacts"
test ! -e "$ACCEPTANCE_ROOT"
```

The shell variable is illustrative; record its resolved absolute value in evidence. Do not use
`$HOME`, `~`, a repository root, or an artist directory as a cleanup target.

## 2. Establish the pure baseline

Use the repository virtual environment. If it is absent, creating it and installing `.[dev]` may
need dependency downloads and therefore separate network approval:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Run and retain complete output:

```bash
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
git diff --check
```

For a clean baseline, compare the observed counts to the release/manifest record; investigate and
record mismatches. Test success is `pass` only for pure/schema/policy behavior.

## 3. Inspect Houdini without cooking

First verify the executable identity and start no UI:

```bash
HYTHON=/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython
test -x "$HYTHON"
"$HYTHON" --version
```

Then run the repository Hython read suite or the integrated read tier. Live tiers must invoke the
entry point with Hython; the integrated CLI rejects them under ordinary Python before creating the
artifact root:

```bash
"$HYTHON" -m pytest tests/hython -o addopts='' -q

"$HYTHON" scripts/run_acceptance.py \
  --execute \
  --tier hython-read \
  --artifact-root "$ACCEPTANCE_ROOT"
```

The read tier may inventory build, license, packages, operators, session, and allowed roots. It must
not cook, save, mutate a graph, start a bridge/model, or install/enable a plugin. A restricted shell
can produce a false Qt/NEON failure; rerun the identical Hython command through the approved native
execution path and record both attempts. Never replace Houdini binaries or global configuration.

## 4. Dry-plan tiered acceptance

List the exact integrated interface and save it with the run:

```bash
.venv/bin/python scripts/run_acceptance.py --help

.venv/bin/python scripts/run_acceptance.py \
  --plan \
  --tier pure \
  --tier hython-read \
  --tier graph-edit \
  --tier single-frame \
  --tier frame-range \
  --tier pdg-child \
  --tier simulation \
  --tier viewport \
  --tier karma \
  --artifact-root "$ACCEPTANCE_ROOT"
```

Review the plan for exact commands, required approvals, fixture source, context/operator types,
fresh paths, frames, points/primitives, seconds, memory, disk/cache bytes, child count, render
resolution, output bytes, plugin state, and cleanup. Remove unapproved tiers; never let the tool
silently downgrade them.

## 5. Execute bounded tiers

Run from least to most costly, stopping on a required `blocked` state:

1. `pure`: schemas, policy, canonical JSON, and deterministic hashes without Houdini.
2. `hython-read`: build/license/operator/package inspection without graph mutation or cooking.
3. `graph-edit`: create a small rebuildable fixture in a disposable `.hipnc`; verify readable
   types, connections, stable IDs, and named output contracts.
4. `single-frame`: cook one declared node/display chain at one frame and record geometry plus
   resource metrics.
5. `frame-range`: expand an inclusive bounded range, record every frame, peak metrics, elapsed
   time, cache bytes, and restoration of the original frame.
6. `pdg-child`: run only allowlisted child commands under the aggregate process/time/memory/disk
   budget; record child identities and termination.
7. `simulation`: use the smallest stateful fixture, explicit range/substeps/cache policy, and no
   implicit cache write.
8. `viewport`: in an isolated Houdini UI session, name viewer, viewport, camera, frame, fresh PNG,
   and resolution; preserve prior camera/UI state.
9. `karma`: exact external-process approval, Karma CPU, one frame unless separately approved,
   conservative resolution at or below 1280x720, time/thread/output-byte limits, and fresh output.

For the accepted cheap G001 live envelope, one exact invocation reaches both bounded cook tiers and
their prerequisites:

```bash
"$HYTHON" scripts/run_acceptance.py \
  --execute \
  --tier single-frame \
  --tier frame-range \
  --artifact-root "$ACCEPTANCE_ROOT"
```

`--allow-pdg-child`, `--allow-simulation`, `--allow-viewport`, and `--allow-karma` are separate,
operator-supplied authorization assertions for their named adapters. They do not activate a
self-hosted runner, change global policy, install a plugin, or grant a different tier. Review the
printed plan and the underlying approval record before supplying any flag. An explicit tier without
its required flag fails closed; an unavailable interactive viewer remains `pending` even when its
flag is present.

## 6. Plugin-disabled and plugin-enabled comparisons

Plugin state is part of evidence identity. Begin from an isolated package path. Run the native
baseline with all optional packages disabled. For SideFX Labs 22.0.368, the locally verified disable
value is:

```bash
HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json "$HYTHON" <approved-read-or-fixture-command>
```

An enabled run is allowed only for the exact installed package manifest/checksum and certified
nodes. Record package JSON hash, installed-tree inventory, exact operator versions, loaded native
binaries, and a separate disable proof. Never infer catalog-wide plugin safety from a fixture.
Plugin install/remove or preference changes are outside this guide.

## 7. Interactive bridge, model, and human/downstream gates

- **Interactive bridge:** use a fresh per-session secret, `127.0.0.1` only, explicit allowed roots,
  and exact single-use approvals. Record request/result hashes, runtime mode, open HIP identity, and
  cleanup. Do not expose `hrpyc` as the production surface.
- **Local model:** probe only an already-running allowlisted loopback service. Do not start a daemon
  or download a model. Record model name/digest, calibration identity, prompt/request/response and
  artifact hashes. Its status is advisory and cannot fill human-owned fields.
- **External model:** requires separately approved network disclosure. Record provider/model,
  endpoint class, data sent, consent, retention setting if known, hashes, and response. If not run,
  use `pending` or `not_applicable` with reason.
- **Human aesthetic review:** present authentic, stable-order evidence and blank rating/winner
  fields. Record the reviewer's exact words and explicit continuation selection. Absence is
  `pending`, never a mechanical failure or an inferred pass.
- **Downstream-app review:** identify app/build, importer/settings, artifact hash, reviewer, observed
  result, and any transformation. Houdini validity alone cannot promote this cell.

## 8. Hash and verify evidence

The merged acceptance summary uses schema `hermes.houdini.acceptance.v1`; canonical JSON is UTF-8,
sorted keys, compact separators, and excludes `summary_sha256` from the payload it hashes. Each tier
records `tier`, `status`, `command`, `started_at`, `duration_seconds`, `budget`, `observed`,
`artifacts`, `warnings`, and `errors`.

Create a separate inventory of retained files from the run root:

```bash
find "$ACCEPTANCE_ROOT" -type f -print0 | sort -z | xargs -0 shasum -a 256
```

Write that output outside any file included in the same hash list, or regenerate after finalizing
the inventory. Rehash from a clean process before promotion. A changed/missing file invalidates its
cell and every downstream cell that depends on it.

## 9. Retention and promotion packet

Retain only manifest-listed evidence:

- acceptance request and canonical summary/hash;
- source commit, workflow/command, environment/build/license/package/plugin inventory;
- full stdout/stderr and policy/approval/process/cleanup logs;
- fixture source identity, `.hipnc` checkpoint when applicable, graph/data manifests;
- authentic viewport/Karma artifacts and mechanical reports;
- model records, exact human feedback, and downstream receipt when actually produced.

Label non-commercial artifacts and keep generated scenes/caches out of Git. The release owner sets
the retention duration and access policy before publication. Do not upload secrets, personal paths
unless required for provenance, arbitrary caches, or unlisted files.

Promote each cell individually according to
[`RELEASE_EVIDENCE_MATRIX.md`](RELEASE_EVIDENCE_MATRIX.md). The technical reviewer may promote
mechanical evidence; plugin, model, human, downstream, and release decisions retain their named
owners. No reviewer may promote evidence outside their authority.

## 10. Cleanup verification

Cleanup is scoped to the exact recorded disposable root and owned process group. Verify targets
before removal; on a shared or uncertain host, quarantine and request review instead of deleting.

1. Stop new bridge/acceptance requests and revoke the per-session secret.
2. Terminate the recorded process group: graceful request, bounded wait, then force only that group
   if necessary. Do not kill processes by a broad `Houdini`, `python`, or `hython` name.
3. Confirm no owned child PIDs, loopback listeners, mounts, or open files remain.
4. Unmount/read-protect artist inputs and quarantine outputs selected for retention.
5. Remove only the resolved fresh job workspace/cache after verifying it is under the disposable
   acceptance parent and is not a symlink. Do not clean global package/license preferences.
6. Record disk before/after, process/listener checks, removed/quarantined paths, exit status, and
   operator. Hash the cleanup record.

A failed cleanup changes the affected runtime cells to `blocked`, quarantines the host, and invokes
the threat model kill switch. It is not downgraded to `warn` merely because tests passed.

## 11. Failure and incident operations

- Source/workflow/environment mismatch: stop before execution; retain inspection output.
- Budget preflight failure: `blocked`; do not raise the budget without a new approval.
- Native cook timeout: stop the owned process group, quarantine partial caches/artifacts, and record
  cooperative-versus-outer termination.
- Hash mismatch: invalidate the artifact and dependants; do not overwrite history.
- Plugin/build/license drift: retain both inventories, disable the plugin, and return to a native
  baseline; do not repair global configuration.
- Credential, persistence, unexpected egress, or path escape: execute the incident procedure in
  [`../security/SELF_HOSTED_HOUDINI_RUNNER_THREAT_MODEL.md`](../security/SELF_HOSTED_HOUDINI_RUNNER_THREAT_MODEL.md),
  quarantine the host, and block activation.
- Missing human/downstream review: preserve `pending` and blank decision fields.

## G001 Lane D interpretation

Lane D is documentation-only. Its own Hython, graph, cook, simulation, viewport, Karma, plugin,
bridge, model, human-aesthetic, and downstream-app cells are `not_applicable`; it makes no live
Houdini claim. Pure regression and Ruff remain required because documentation must not regress the
repository. Integrated G001 evidence must be populated by the integration captain from the actual
Lane A/B/C interfaces and live runs, leaving every unrun rung explicitly `pending` or
`not_applicable` with a reason.
