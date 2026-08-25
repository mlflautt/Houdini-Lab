# G001 Copy-Paste Worker Prompts

These are the only prompts the human orchestrator needs to paste into new Codex sessions. Launch
workers A-D only after G001 has been explicitly accepted. Use a separate Codex session and isolated
Git worktree for each worker.

## Accept the cycle first

Paste this in the main orchestrator session:

```text
Accept Grinder Cycle G001 and launch lanes A-D from v0.30.0.
```

Wait until the orchestrator confirms that the manifest is accepted and the four worktrees/branches
are ready. Then open four new Codex sessions and paste one prompt into each.

## Worker A

```text
Execute Grinder worker G001-A: read /Users/m1/Houdini Lab/docs/grinder/cycles/G001-v035-live-verification/LANE_A_ACCEPTANCE_CORE.md and follow it exactly from start to finish; work only in the isolated G001-A worktree, push the completed branch and open the required component PR, but do not merge it.
```

## Worker B

```text
Execute Grinder worker G001-B: read /Users/m1/Houdini Lab/docs/grinder/cycles/G001-v035-live-verification/LANE_B_HYTHON_TIERS.md and follow it exactly from start to finish; work only in the isolated G001-B worktree, push the completed branch and open the required component PR, but do not merge it.
```

## Worker C

```text
Execute Grinder worker G001-C: read /Users/m1/Houdini Lab/docs/grinder/cycles/G001-v035-live-verification/LANE_C_COMPATIBILITY_BASELINES.md and follow it exactly from start to finish; work only in the isolated G001-C worktree, push the completed branch and open the required component PR, but do not merge it.
```

## Worker D

```text
Execute Grinder worker G001-D: read /Users/m1/Houdini Lab/docs/grinder/cycles/G001-v035-live-verification/LANE_D_RUNNER_GOVERNANCE.md and follow it exactly from start to finish; work only in the isolated G001-D worktree, push the completed branch and open the required component PR, but do not merge it.
```

## Integration captain

Do not launch this session until workers A-D have finished and each has supplied a PR URL, full
commit SHA, and committed receipt.

```text
Execute the G001 integration captain: read /Users/m1/Houdini Lab/docs/grinder/cycles/G001-v035-live-verification/INTEGRATION_CAPTAIN.md and follow it exactly from start to finish, using the completed A-D PRs, head commits, and receipts as inputs; integrate through the protected-main PR flow and do not invent or silently waive missing evidence.
```

## If a worker cannot find its isolated worktree

Paste this single correction into that worker session:

```text
Stop without editing main. Read /Users/m1/Houdini Lab/docs/grinder/cycles/G001-v035-live-verification/LAUNCH_CHECKLIST.md, create or locate the exact isolated worktree and branch assigned to your lane from the frozen v0.30.0 commit, switch your task to that worktree, and then resume your lane brief.
```

