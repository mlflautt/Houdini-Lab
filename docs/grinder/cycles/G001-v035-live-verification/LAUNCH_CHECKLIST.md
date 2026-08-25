# G001 Launch Checklist

Use this checklist once the owner has accepted G001. It is written for the human orchestrator
creating separate Codex tasks.

## 1. Freeze the planning package

- Merge the Grinder planning PR to `main`.
- Confirm tag `v0.30.0` resolves to
  `b8b8f4c4b702b4f895bbee3098c90006541a7373`.
- Change the cycle state from `PROPOSED` to `ACCEPTED`, add the acceptance date, and commit that
  manifest-only change before dispatch.
- Do not retag or move `v0.30.0`.

## 2. Create isolated workspaces

Use one clean worktree or clone per lane. Create each branch from the full base SHA, not current
`main`:

```bash
git fetch origin --tags --prune
git worktree add ../houdini-g001-a -b codex/grinder-g001-a-acceptance-core b8b8f4c4b702b4f895bbee3098c90006541a7373
git worktree add ../houdini-g001-b -b codex/grinder-g001-b-hython-tiers b8b8f4c4b702b4f895bbee3098c90006541a7373
git worktree add ../houdini-g001-c -b codex/grinder-g001-c-compatibility-baselines b8b8f4c4b702b4f895bbee3098c90006541a7373
git worktree add ../houdini-g001-d -b codex/grinder-g001-d-runner-governance b8b8f4c4b702b4f895bbee3098c90006541a7373
```

Because the cycle documents are newer than the base tag, place the accepted instruction file in
each Codex task prompt or copy only the read-only `docs/grinder/` planning package into the
worktree. Do not commit that copied package on the lane branch except for the lane's receipt.

## 3. Dispatch four tasks

Give each task exactly one lane brief. Begin the prompt with:

> Execute this accepted Grinder lane exactly as written. Treat the attached lane brief and G001
> manifest as the complete execution contract. Start from the frozen commit, respect file
> ownership, make reasonable in-scope decisions, stop on listed conditions, and finish with a
> pushed branch, PR, and committed receipt. Do not merge other lanes or alter shared metadata.

Attach or paste:

- `CYCLE_MANIFEST.md`;
- the matching `LANE_*.md`;
- `templates/LANE_RECEIPT_TEMPLATE.md`;
- if the instance cannot see the planning merge, `GRINDER_ARCHITECTURE.md`.

## 4. Monitor by receipts, not chat summaries

For each lane verify:

- its starting SHA equals the frozen base;
- its diff contains only owned paths;
- its receipt includes exact commands/results and a head SHA;
- its component PR targets `main`, is reviewable, and remains unmerged;
- `pending` evidence is not described as passing.

Do not ask one lane to repair another lane's branch. Amend the manifest or return work to its owner.

## 5. Dispatch integration

After A-D are ready, create a fresh integration worktree and task:

```bash
git worktree add ../houdini-g001-integration -b codex/grinder-g001-integration b8b8f4c4b702b4f895bbee3098c90006541a7373
```

Give that instance the manifest, all four receipts, PR URLs/head SHAs, and
`INTEGRATION_CAPTAIN.md`. The captain alone changes shared metadata and opens the final PR to
`main`. After the integrated PR merges, close the superseded component PRs with a link to the
integrated PR; do not merge them separately.

## 6. Release boundary

Merging the integrated PR and tagging `v0.35.0` are separate actions. The release occurs only after
final-main CI and the integrated evidence matrix are reviewed. Self-hosted runner activation is a
different future approval and must not ride along with this release.
