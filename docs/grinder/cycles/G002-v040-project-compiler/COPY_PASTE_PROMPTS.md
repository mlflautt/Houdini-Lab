# G002 Copy-Paste Worker Prompts

Do not use these prompts while the manifest says `PROPOSED` or contains a base placeholder. After
acceptance, the orchestrator creates the four exact worktrees in `LAUNCH_CHECKLIST.md`. Then paste
one sentence into each new Codex session.

## Worker A

```text
Execute Grinder worker G002-A in the prepared worktree /Users/m1/houdini-g002-a: read /Users/m1/Houdini Lab/docs/grinder/cycles/G002-v040-project-compiler/LANE_A_PROJECT_SPEC.md and follow it exactly from start to finish; push the completed branch and open the required component PR, but do not merge it.
```

## Worker B

```text
Execute Grinder worker G002-B in the prepared worktree /Users/m1/houdini-g002-b: read /Users/m1/Houdini Lab/docs/grinder/cycles/G002-v040-project-compiler/LANE_B_CONTRACT_ADAPTERS.md and follow it exactly from start to finish; push the completed branch and open the required component PR, but do not merge it.
```

## Worker C

```text
Execute Grinder worker G002-C in the prepared worktree /Users/m1/houdini-g002-c: read /Users/m1/Houdini Lab/docs/grinder/cycles/G002-v040-project-compiler/LANE_C_DAG_COMPILER.md and follow it exactly from start to finish; push the completed branch and open the required component PR, but do not merge it.
```

## Worker D

```text
Execute Grinder worker G002-D in the prepared worktree /Users/m1/houdini-g002-d: read /Users/m1/Houdini Lab/docs/grinder/cycles/G002-v040-project-compiler/LANE_D_OBSERVER_DRIFT.md and follow it exactly from start to finish; push the completed branch and open the required component PR, but do not merge it.
```

## Integration captain

Launch only after A-D each provide a pushed head, component PR, committed receipt, exact gate
results, and scope-clean diff.

```text
Execute the G002 integration captain in its prepared integration worktree: read /Users/m1/Houdini Lab/docs/grinder/cycles/G002-v040-project-compiler/INTEGRATION_CAPTAIN.md and follow it exactly using the completed G002 A-D PRs, heads, and receipts; integrate through protected main and preserve every unrun runtime or human gate as not_applicable or pending.
```
