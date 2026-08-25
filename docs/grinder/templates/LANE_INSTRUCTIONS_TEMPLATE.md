# Grinder Lane `<cycle>-<lane>` — `<title>`

> Copy this file into a cycle directory and replace every angle-bracket field before dispatch.

## Mission

One paragraph describing the bounded outcome and why it advances the cycle.

## Frozen execution contract

- Cycle state: `ACCEPTED`
- Repository: `<owner/repository>`
- Local repository root: `<absolute path>`
- Base tag: `<tag>`
- Base commit: `<full SHA>`
- Branch: `codex/grinder-<cycle>-<lane>-<slug>`
- Target Houdini: `<edition and build>`
- License: `<license>`
- Depends on other lanes: `none` or explicit frozen contract
- Merge authority: integration captain only

If any value does not match reality, stop and report the mismatch. Do not silently choose a newer
base.

## Read before editing

List the root agent instructions, architecture, roadmap section, cycle manifest, this brief, and
the narrow implementation references needed by the lane. State that these files are read-only.

## Startup preflight

Provide exact commands to verify the repository, clean worktree, base commit, remote, toolchain,
and dependency environment. Include a safe setup path if the repository virtual environment is
absent. Never authorize global installs implicitly.

## Owned paths

Enumerate every file or narrow path the lane may create/edit. Then enumerate integration-owned and
forbidden hotspots. The lane must stop before crossing this boundary.

## Required contracts

Specify public data structures, status vocabularies, command behavior, risk/cook semantics, and
error behavior. Consumers should be able to integrate the lane from this section alone.

## Implementation sequence

Give a bounded ordered sequence. Separate pure implementation, Houdini-bound work, evidence, and
documentation. Require lazy `hou` imports when applicable.

## Acceptance gates

List exact targeted, pure, lint, Hython, visual, and scope commands. State which gates may be
`pending` and which must pass.

## Required receipt and handoff

Require `docs/grinder/receipts/<cycle>-<lane>.md`, one or more ordinary commits, pushed branch, and
a PR. Include the exact final response fields: branch, commit, PR URL, changed files, commands and
results, evidence statuses, deviations, blockers, integration notes.

## Stop conditions and non-goals

Repeat lane-specific policy, ownership, cost, and architecture boundaries. Explicit non-goals are
part of the contract, not optional advice.

