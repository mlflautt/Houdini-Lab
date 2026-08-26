# G002 Launch Checklist

Use only after the G001 integration is merged, its release base is tagged, every manifest base
placeholder is replaced, and the owner explicitly accepts G002.

## 1. Freeze and verify

- Fetch `origin` and tags; verify the manifest tag resolves to its full SHA.
- Confirm the G002 planning PR is merged and the manifest says `ACCEPTED` with date/instruction.
- Confirm root `main` is clean and synchronized; do not move the base tag.
- Run pure/Ruff baseline and record actual counts for lane comparison.
- Verify `gh auth status --hostname github.com` and `ssh -T git@github.com` independently.

## 2. Create isolated worktrees

Replace `<BASE_SHA>` below only with the accepted full manifest SHA:

```bash
git fetch origin --tags --prune
git worktree add /Users/m1/houdini-g002-a -b codex/grinder-g002-a-project-spec <BASE_SHA>
git worktree add /Users/m1/houdini-g002-b -b codex/grinder-g002-b-contract-adapters <BASE_SHA>
git worktree add /Users/m1/houdini-g002-c -b codex/grinder-g002-c-dag-compiler <BASE_SHA>
git worktree add /Users/m1/houdini-g002-d -b codex/grinder-g002-d-observer-drift <BASE_SHA>
```

For each worktree verify top-level, clean branch, exact HEAD, remote, and that the accepted planning
files are visible. If the instruction package is newer than the frozen base, provide its absolute
main-worktree path in the prompt; do not commit copied planning files on lane branches except the
owned receipt.

## 3. Dispatch and monitor

Paste the four one-line prompts from `COPY_PASTE_PROMPTS.md` into four separate Codex sessions.
Monitor committed receipts and PR heads, not chat summaries. A lane is ready only when:

- its diff contains only owned paths;
- targeted/full pure and Ruff gates pass;
- its receipt records exact base/head/files/commands/results;
- its branch is pushed and component PR remains unmerged;
- every runtime/human claim is correctly `not_applicable` or pending.

Do not ask one worker to repair another branch. Return defects to the owner lane or amend the
manifest with human approval.

## 4. Dispatch integration

After A-D are ready:

```bash
git worktree add /Users/m1/houdini-g002-integration -b codex/grinder-g002-integration <BASE_SHA>
```

Give the integration session all four PR URLs, full heads, committed receipts, the accepted
manifest, and `INTEGRATION_CAPTAIN.md`. The captain integrates A→B→C→D, creates the shared pipeline,
dry Living Biome fixture, and protected-main PR. Close component PRs only after integration merges.

## 5. Boundary after G002

Do not launch G003 merely because G002 lanes are ready. G003 requires the merged G002 source/tag,
an audit of actual public APIs, an H22 parameter probe for any live adapters, a new accepted
manifest, and separate runtime approvals.
