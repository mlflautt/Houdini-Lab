# G003 Launch Checklist

Do not execute this checklist while `CYCLE_MANIFEST.md` is `PROPOSED` or motion is `UNSET`.

## 1. Freeze owner decision and baseline

- Record the owner's exact motion sentence in the manifest and freeze ID/version, candidate outputs,
  risk, frame/resource ceilings, and any native-only restriction.
- Obtain explicit cycle acceptance and change state to `ACCEPTED` with date/instruction.
- Fetch/prune origin; verify `origin/main` and all lane bases equal the manifest's full SHA.
- Verify clean root, `gh auth status`, SSH greeting, pure/Ruff baseline, H22.0.368 installation and
  Apprentice license. Do not install plugins or alter global Houdini configuration.

## 2. Create isolated worktrees

```bash
git fetch origin --tags --prune
git worktree add /Users/m1/houdini-g003-a -b codex/grinder-g003-a-run-governor 44727325ecb5262a613d259d6db2ff23274ed211
git worktree add /Users/m1/houdini-g003-b -b codex/grinder-g003-b-sop-composition 44727325ecb5262a613d259d6db2ff23274ed211
git worktree add /Users/m1/houdini-g003-c -b codex/grinder-g003-c-solaris-assembly 44727325ecb5262a613d259d6db2ff23274ed211
git worktree add /Users/m1/houdini-g003-d -b codex/grinder-g003-d-run-receipt 44727325ecb5262a613d259d6db2ff23274ed211
```

Verify each cwd, branch, clean status, exact HEAD, remote, accepted manifest, and lane brief. Create a
project `.venv` in each worktree if needed. Planning files must already be merged to main before
dispatch; do not point workers at an unmerged planning checkout.

## 3. Dispatch and readiness

Paste one sentence per lane from `COPY_PASTE_PROMPTS.md` into four separate Codex sessions. A lane is
ready only when owned-path diff, exact base/head, targeted/full pure, Ruff, read-only probes where
required, committed receipt, pushed branch, and unmerged component PR are all verified. Runtime or
creative claims must be pending/not applicable. Return defects to the owning lane.

## 4. Integration worktree

After all four lanes are ready:

```bash
git worktree add /Users/m1/houdini-g003-integration -b codex/grinder-g003-integration 44727325ecb5262a613d259d6db2ff23274ed211
```

Give the captain the four PR URLs/full heads/receipts and `INTEGRATION_CAPTAIN.md`. Dispatching the
captain does not pre-authorize live mutation. The captain must stop after the final dry run manifest
and obtain exact graph/data approval before executing it.

## 5. Completion boundary

Merge only through protected main and verify final-main CI. Do not tag `v0.40.0`, publish a GitHub
release, enable a runner, install plugins, run Karma, or choose a biome without separate authority.
