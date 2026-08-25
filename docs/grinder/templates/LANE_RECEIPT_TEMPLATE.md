# Grinder Lane Receipt `<cycle>-<lane>`

- Lane: `<cycle>-<lane>`
- Status: `ready | blocked`
- Base tag: `<tag>`
- Base commit: `<full SHA>`
- Branch: `<branch>`
- Head commit: `<full SHA>`
- Pull request: `<URL or pending>`
- Agent/runtime: `<Codex/model if known>`
- Date: `<YYYY-MM-DD>`

## Delivered contract

Describe what now exists in terms a fresh integration captain can verify. Do not copy the mission
unchanged if the implementation diverged.

## Changed files

List every committed file. Confirm that the list is within lane ownership.

## Verification

| Gate | Status | Exact command | Result or artifact |
|---|---|---|---|
| Scope |  |  |  |
| Targeted pure |  |  |  |
| Full pure |  |  |  |
| Ruff |  |  |  |
| Hython |  |  |  |
| Graph/data/visual |  |  |  |

Allowed statuses: `pass`, `warn`, `pending`, `blocked`, `not_applicable`.

## Contract and integration notes

Record import surfaces, CLI behavior, schema versions, assumptions, and the exact integration work
left for the captain.

## Deviations and unresolved work

Record every deviation from the lane brief, failed or unavailable gate, pre-existing failure, and
follow-up. Use `none` only after checking.

## Artifacts and provenance

List non-Git artifacts with absolute path, purpose, and SHA-256 where practical. Mark disposable
artifacts. Do not imply that an artifact exists if its gate did not run.

