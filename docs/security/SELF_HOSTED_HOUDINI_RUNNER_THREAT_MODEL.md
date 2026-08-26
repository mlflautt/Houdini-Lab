# Self-Hosted Houdini Runner Threat Model

- Design status: `proposal`
- Activation status: `blocked`
- Scope: a future dedicated macOS runner for Houdini Apprentice 22.0.368
- Review owner: repository owner
- Operational owner: named runner custodian (unassigned)
- Security review cadence: before activation, quarterly while enabled, and after every incident or
  material drift event
- Last reviewed: 2026-08-25

This document makes a future runner reviewable. It does **not** authorize registration, change a
workflow, install software, automate a license, or place a credential on a host. G001 cannot turn
this design into an active service. Activation requires the separate human checkpoint in
[Activation prerequisites](#activation-prerequisites-and-human-checkpoint).

## Claim labels

- **Documented fact**: established by a cited repository file or authoritative external source.
- **Inference**: a conclusion drawn from documented facts; it must be verified on the actual host.
- **Proposal**: a control or operating decision that does not exist until separately implemented
  and evidenced.

## Scope and security objective

The protected target is a Houdini-capable macOS host, its node-locked non-commercial license, and
the repository and evidence it processes. A job is hostile until its immutable commit, event,
actor, workflow, dependencies, requested tiers, and approval have all passed admission policy.
The runner must fail closed before checkout or Houdini launch when any required identity is absent.

The design assumes no strong macOS container boundary for Houdini. **Inference:** process and
workspace cleanup on a reused machine cannot prove that hostile code left no persistence. Therefore
public/fork pull-request code is never eligible, and collaborator pull-request code is eligible
only after human review and promotion to an immutable protected ref. The preferred end state is a
one-job just-in-time runner plus host reimaging; a merely persistent runner is insufficient.

## Current repository trust inventory

The baseline workflow [`../../.github/workflows/ci.yml`](../../.github/workflows/ci.yml) runs on
`push` to `main`, all `pull_request` targets, and manual dispatch. It declares
`permissions: contents: read`, uses GitHub-hosted `macos-latest`, references
`actions/checkout@v6` and `actions/setup-python@v6` by tag, installs `.[dev]`, and runs pure tests and
Ruff. Its Hython job is explicitly disabled with `if: false` and also targets `macos-latest`.
These are repository facts, not claims about live GitHub settings.

The repository supplies additional controls that a runner must preserve:

- the bridge is signed, bounded, loopback-only, and approval-gated
  ([`../bridge.md`](../bridge.md));
- filesystem writes resolve through allowlisted roots, including symlinks;
- cooks declare scope and time/memory/topology/frame budgets, while an in-process native cook has
  only cooperative interruption ([`../resource-control.md`](../resource-control.md));
- plugin records pin build, license, permissions, checksum, enable/disable boundary, and bounded
  fixtures; an allowed package is not catalog-wide certification
  ([`../../plugins/README.md`](../../plugins/README.md));
- Apprentice is non-commercial, uses `.hipnc`/`.hdanc`, does not permit Houdini Engine or
  third-party renderers, and its license is node-locked
  ([`../apprentice-constraints.md`](../apprentice-constraints.md)).

**Inference:** none of these application controls is a host sandbox. A checked-out workflow can
invoke shell commands before Hermes policy is imported, so admission and host isolation must sit
outside the repository under test.

## Assets and security properties

| Asset | Required property | Impact if lost |
|---|---|---|
| Repository refs and worktree | integrity, immutable input identity | malicious code accepted or evidence bound to the wrong source |
| Artist `.hipnc`, assets, references, and feedback | confidentiality, integrity, lineage | privacy loss, overwrite, or false creative provenance |
| SideFX credentials and license state | confidentiality, availability, license compliance | credential theft, invalid activation, or Houdini outage |
| GitHub registration token, job token, and any SSH keys | confidentiality, least privilege, short lifetime | repository or runner control |
| Houdini/plugin/package caches | integrity, isolation by identity | persistent execution or contaminated results |
| Evidence, renders, logs, and hashes | integrity, authenticity, retention | false release claims or missing incident record |
| Bridge session secret | confidentiality, single-session lifetime | unauthorized live Houdini commands |
| User identity, paths, scene contents, and model prompts | confidentiality, minimization | personal or project data disclosure |
| Runner host and artist workstation availability | bounded resource use, recoverability | denial of service or interruption of interactive work |

## Trust boundaries and admitted flows

```text
public/fork PR --------X
collaborator PR -------X---- review + immutable promotion ----+
protected main/tag -------------------------------------------+--> admission controller
workflow file/action refs ------------------------------------+        |
GitHub service <---- HTTPS egress + job credential --------------------+
                                                                    one job
dedicated account -> ephemeral workspace -> allowlisted launcher -> Houdini/children
                                               |                   |      |
                                               +-> audit log       |      +-> husk/PDG child
                                                                   +-> 127.0.0.1 bridge
                                                                   +-> approved plugins/cache
```

Boundaries requiring an explicit policy decision are: public/fork PR versus collaborator PR;
unreviewed collaborator code versus protected main/release/tag; GitHub service versus runner;
runner daemon versus job process; job worktree versus host; Houdini process versus licensing;
loopback bridge versus its clients; Houdini versus child processes; base package set versus optional
plugins; isolated job cache versus uploaded artifact; and automation evidence versus human or
downstream review.

## Abuse cases, controls, and residual risk

| ID | Threat / abuse case | Required preventive and detective controls | Residual risk and disposition |
|---|---|---|---|
| T01 | Untrusted PR code executes on the host | Deny `pull_request`, `pull_request_target`, fork, and arbitrary `workflow_dispatch` inputs at the runner admission layer. Accept only an allowlisted workflow SHA and immutable protected main/tag SHA after human review. No secrets on rejected events. | A compromised maintainer or protected ref can still admit hostile code. Repository owner reviews branch protection and audit log quarterly. |
| T02 | A job persists into later jobs | Prefer one-job JIT registration and reimage from a sealed host baseline. Use a fresh APFS volume or disposable VM when Houdini support permits; otherwise wipe a dedicated workspace, caches, temp, launch agents, and process table, then verify against the baseline before re-registration. | Cleanup on a reused macOS host is not a proof of non-persistence. Activation remains blocked until the owner accepts the isolation method. |
| T03 | GitHub token, SSH key, bridge secret, or SideFX credential is exfiltrated | Dedicated least-privilege account; no personal SSH agent/keychain; read-only job token; short-lived registration; bridge secret generated per job and removed at teardown; no repository or environment secrets for untrusted events; redact logs; deny outbound network by default. | GitHub traffic and explicitly approved artifact upload still provide exfiltration channels. Security owner tests egress and redaction before activation. |
| T04 | Symlink or path traversal escapes the workspace | Resolve every input/output/cache path before use; reject symlink components that resolve outside the per-job roots; mount artist files read-only through an explicit allowlist; refuse overwrites; archive by enumerated manifest, never a broad glob. | Houdini/plugins may open undeclared paths internally. Runner custodian compares file-access telemetry during fixtures and after package drift. |
| T05 | Fork/secrets assumptions are wrong or settings drift | Admission uses event payload and base/head identities, not secret absence as a trust signal. Snapshot repository Actions settings before each activation window and fail if they differ from the approved record. | GitHub settings are outside this repository and were not inspected in G001. They are an activation blocker. |
| T06 | A PR mutates its workflow or uses a movable action tag | Execute the reviewed workflow from the protected base, compare its SHA to an allowlist, deny workflow-path changes for Houdini jobs, pin every action to a reviewed full commit SHA, and restrict allowed actions. | Current workflow actions are tag-pinned; no workflow change is owned by Lane D. Pinning is an activation prerequisite for a later approved change. |
| T07 | Cache or artifact poisoning causes execution or false evidence | Disable cross-trust cache restore; namespace by repository, immutable commit, Houdini build, package inventory, plugin state, license, architecture, and schema; verify hashes before use; treat downloaded artifacts as data; never execute restored cache content; upload a signed manifest from a clean post-job step. | A compromised admitted job can produce internally consistent false artifacts. Human/runtime provenance review remains required for promotion. |
| T08 | A plugin loads code at startup | Start with a sealed package path and plugins disabled; inventory package JSON and loaded operators; enable only exact audited package/build/checksum in an isolated tier; run an explicit disabled comparison; never inherit user preference package paths. | Certified nodes do not certify a whole package. Plugin owner re-reviews on any package or build drift. |
| T09 | Broad `hou`, Python, VEX, shell, or workflow code escapes registered policy | Launcher exposes only tier-specific allowlisted commands and arguments. Keep safe mode; deny arbitrary code and development/privileged-local modes. Review fixtures as code before promotion. Use an OS account with no admin/sudo. | Houdini and Python are general-purpose processes; reviewed repository code remains powerful. This is accepted only for protected immutable refs on a dedicated host. |
| T10 | Network egress leaks data or downloads mutable dependencies | Default-deny outbound policy. Allow only documented GitHub endpoints during runner control/artifact upload and no network during Houdini execution. Prebuild the reviewed environment; fail rather than `pip`, plugin, model, or asset download. Log destinations and byte counts. | GitHub endpoint allowlisting can be broad and endpoints may change. Network owner reviews exceptions quarterly. |
| T11 | CPU, memory, disk, frames, or output bytes exhaust the host | Per-tier hard wall timeout outside Houdini, process-group termination, disk quota/free-space floor, memory/CPU monitor, explicit point/primitive/frame/render budgets, 1280x720 repository ceiling, and artifact byte cap. | Native cook interruption is cooperative; the outer process may require force termination. Preserve incident logs, not a half-trusted cache. |
| T12 | Concurrent Houdini sessions exhaust a node-locked license or corrupt shared state | Runner group and host concurrency `1`; host lock acquired before license probe and held through cleanup; deny if Houdini/hython/husk/hserver state is unexpected; no artist session on the host. | SideFX license behavior and process interaction must be probed on the dedicated host. License owner decides whether a failed/stale state needs manual recovery. |
| T13 | Stale Houdini, child, daemon, or render processes survive cancellation | Launch the whole job in a distinct process group; record child PIDs/start times; TERM, bounded wait, then KILL only the owned group; verify no owned descendants/listeners remain before release. Never kill by broad name on a shared host. | A process can daemonize or change identity. Reimage/quarantine is the fallback, not blind process-name killing. |
| T14 | Automation interferes with the user's session, UI, keyboard, or files | Dedicated headless account and host; no login items, iCloud/personal mounts, GUI automation, active desktop, selection/pane reliance, or access to the artist home. Interactive viewport evidence uses an isolated disposable session only. | Some visual capture may require a GUI session. That capability stays blocked until an isolated GUI test account is demonstrated. |
| T15 | Concurrent jobs or stale workspaces mix evidence | One active job; unique run ID and fresh non-existing roots; exclusive host lock; atomic writes; evidence manifest binds all artifacts to commit/run/environment; refuse pre-existing output. | Operator error can upload the wrong root. Promotion requires manifest/hash verification from a separate clean process. |
| T16 | Malicious or malformed artifact harms a reviewer/downstream app | Restrict formats and sizes; validate parser input; render previews in a sandboxed review environment; never auto-open files or import `.hipnc` into artist work; downstream review receives hashes and non-commercial label. | Complex formats can contain parser exploits or scripts. Downstream owner chooses an isolated review method. |
| T17 | Audit evidence or cleanup logs are altered by the job | Stream runner and policy logs to append-only storage outside the job account; record admission decision, ref/workflow/action identities, process tree, network events, budgets, cleanup result, and artifact hashes. | A compromised host may falsify local telemetry. External GitHub records and independently rehashed artifacts provide partial corroboration. |
| T18 | The runner becomes unavailable or blocks releases | Runner evidence is a named optional/required gate per release; queue timeout and kill switch are explicit; pure GitHub-hosted CI remains separate; no automatic downgrade from live evidence to pure evidence. | Live evidence may remain `pending` or `blocked`; release owner decides according to the declared matrix, never a generic green check. |

## Required control design

### Host and identity

**Proposal:** use a dedicated Apple-silicon Mac with a standard non-admin `houdini-ci` account and
no personal sign-in, SSH keys, cloud storage, browser session, developer secrets, unrelated
repositories, or artist files. FileVault, OS patching, screen lock, and physical access belong to a
named host owner. The host image records macOS, Houdini, runner, Python, Xcode/CLI tools, package
inventory, and checksums. Drift blocks a job rather than silently updating.

### Admission policy

Before checkout, a small root-owned launcher must verify all of the following and log the decision:

1. repository identity, event name, actor, immutable head/base SHA, protected-ref state, and
   allowlisted workflow SHA;
2. no forbidden workflow change and only full-SHA-pinned actions;
3. required human approval bound to that exact SHA and requested tiers;
4. runner group/labels route only the approved workflow;
5. job token permissions are read-only and no environment secrets are exposed;
6. host image/package/license fingerprints match the approved baseline;
7. exclusive host lock, clean process table, fresh workspace, disk floor, and kill switch are ready.

No criterion may be inferred from a branch name alone.

### Job lifecycle

1. Allocate a new non-existing run root and cache namespace; record host and source identity.
2. Check out the exact commit without credentials retained in Git configuration.
3. Verify dependency lock/materialized environment without network installation.
4. Run only the approved tier sequence with one outer wall clock and per-tier budgets.
5. Launch Houdini and every child in the owned process group; bind the authenticated bridge only to
   `127.0.0.1`; use a per-job secret and explicit allowed roots.
6. Hash artifacts and the canonical acceptance summary; upload only manifest-listed files.
7. Revoke job/bridge credentials, terminate the owned group, unmount inputs, quarantine outputs,
   clear the job workspace/cache, and run cleanup verification.
8. Forward logs externally and deregister the one-job runner. Any failed cleanup quarantines the
   host and prevents new registration.

### Resource envelope

Concurrency is exactly one Houdini job per host. Each tier must declare time, memory, disk, points,
primitives, frame count, resolution, process count, and output-byte ceilings. The outer supervisor,
not Houdini alone, enforces wall time and owns process-group termination. PDG children inherit the
same environment, egress policy, root, and aggregate budget; they cannot register additional
runners or escape the process group.

### Cache and artifact policy

Use no cache across untrusted identities. Approved protected refs may use read-only, content-addressed
caches created by a trusted build job; job output never overwrites them. Retain the acceptance
summary, hashes, policy/admission log, environment inventory, cleanup result, and promoted evidence
for the release retention period. Large `.hipnc`, render, and cache artifacts remain outside Git and
are labeled non-commercial. Retention duration and storage access are unresolved owner decisions.

## Residual-risk register

| Risk | Owner | Review cadence | Required decision |
|---|---|---|---|
| No strong isolation guarantee for native Houdini on reused macOS | repository owner | before activation and quarterly | accept dedicated reimaged host/VM design or keep blocked |
| General-purpose execution in reviewed repository code | security reviewer | every admitted SHA | approve exact ref and tier set |
| Node-locked license availability and stale license processes | license owner | before every run and on SideFX/build drift | approve non-interactive use and recovery procedure |
| GitHub settings, runner groups, environment approvals, and token scope not inspected by G001 | repository admin | before activation and monthly | capture and approve settings evidence |
| Action tags in current workflow are movable | workflow owner | before activation and dependency updates | land a separately reviewed full-SHA pinning change |
| Default-deny egress implementation and GitHub exception set undefined | network owner | before activation and quarterly | approve tested policy and logs |
| GUI viewport capture may require a user session | host owner | before viewport tier | demonstrate isolated account or leave tier blocked |
| Retention duration, immutable log store, and privacy deletion process undefined | repository owner | before activation and annually | approve data handling schedule |

## Incident, rollback, and kill switch

The kill switch has two independent parts: disable runner assignment at GitHub and disable the
local launch service. Either action must stop new work. A job-level stop revokes its credential,
terminates only its recorded process group, and marks all outputs untrusted.

On suspected compromise or policy failure:

1. stop assignment and the local launcher; do not start cleanup scripts supplied by the job;
2. disconnect nonessential network access and preserve external logs, event payload, commit,
   workflow, process tree, hashes, and timestamps;
3. revoke runner registration, job/environment credentials, bridge secret, and any exposed keys;
4. quarantine the host and every cache/artifact from the run; mark affected release cells
   `blocked` and invalidate evidence derived from them;
5. reimage from the sealed baseline, rotate credentials, and re-establish host/license fingerprints;
6. document cause, scope, cleanup evidence, and control change; obtain repository-owner and security
   approval before re-enabling either half of the kill switch.

Rollback means returning to the GitHub-hosted pure workflow with the Hython runner disabled. It does
not mean accepting pure CI as proof of unrun Houdini tiers.

## Activation prerequisites and human checkpoint

All boxes are intentionally unchecked. Evidence must be attached to a separate design-review
record; a merge of G001 does not check any box.

- [ ] Repository owner approves this threat model and every accepted residual risk.
- [ ] A separate human explicitly writes `APPROVE SELF-HOSTED HOUDINI RUNNER ACTIVATION` and binds
      it to a reviewed implementation revision. No agent may infer this approval.
- [ ] Dedicated host/account or stronger disposable isolation is built and reimage-tested.
- [ ] GitHub repository visibility, branch protection, Actions settings, runner group, environment
      approvals, fork policy, and token permissions are captured and reviewed.
- [ ] Eligible workflow is full-SHA action-pinned, immutable, least-privilege, and denies untrusted
      events before checkout.
- [ ] JIT/ephemeral registration, external runner logs, and both kill-switch halves are tested.
- [ ] Default-deny egress and exact exceptions are tested; Houdini tiers work with network denied.
- [ ] Fresh workspace, path/symlink containment, cache separation, artifact allowlist, hash binding,
      retention, and verified cleanup are demonstrated.
- [ ] Time/memory/disk/process/frame/resolution/output limits and process-group termination are
      exercised with intentional failures.
- [ ] Houdini Apprentice build/license/non-commercial behavior, concurrency one, stale-process
      recovery, and non-interactive license policy are approved by the license owner.
- [ ] Plugins-disabled baseline and each exact optional plugin enable/disable fixture are proven.
- [ ] Bridge loopback/authentication/secret lifecycle and GUI-session isolation are proven.
- [ ] Incident drill quarantines a run, revokes credentials, reimages the host, and leaves the
      runner disabled until reapproval.

Until every applicable item has evidence and the separate phrase is recorded, status remains
`blocked` and `.github/workflows/ci.yml` must retain `if: false` for Hython.

## Sources and claim ledger

Accessed 2026-08-25:

- **Documented fact — repository:** [`../architecture.md`](../architecture.md),
  [`../bridge.md`](../bridge.md), [`../resource-control.md`](../resource-control.md),
  [`../apprentice-constraints.md`](../apprentice-constraints.md),
  [`../../plugins/README.md`](../../plugins/README.md), and
  [`../../.github/workflows/ci.yml`](../../.github/workflows/ci.yml).
- **Documented fact — GitHub:** [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
  states that self-hosted runners lack clean-ephemeral guarantees, can be persistently compromised,
  and supports JIT runners; [self-hosted runners reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners)
  recommends ephemeral autoscaling and external preservation of ephemeral runner logs.
- **Documented fact — GitHub:** [events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
  documents fork secret and token behavior; [repository Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
  documents fork approval/settings controls. This design does not rely on those defaults alone.
- **Documented fact — GitHub:** [Protecting against security threats](https://docs.github.com/en/code-security/tutorials/secure-your-organization/protect-against-threats)
  recommends explicit least-privilege workflow permissions, full commit-SHA action pinning, and
  action allowlisting.
- **Documented fact — SideFX:** [Apprentice FAQs](https://www.sidefx.com/faq/apprentice/)
  documents non-commercial use, node-locked/non-floating licenses, restricted formats/rendering,
  and no third-party renderers.
- **Inference:** the threat conclusions and residual-risk judgments above combine those facts with
  the current repository implementation. They require verification on the proposed host.
- **Proposal:** every future-state control, owner assignment, cadence, admission rule, retention
  choice, and activation checklist item remains unimplemented until separately approved and proven.
