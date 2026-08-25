# Houdini Lab Grinder

The Grinder is the repository's development control plane. It converts the grand roadmap into
bounded, parallel cycles that independent Codex instances can execute without sharing hidden
conversation state.

It is deliberately separate from the Hermes/Houdini runtime control plane. The runtime controls
Houdini work; the Grinder controls how this repository is changed.

## Start here

1. Read [the Grinder architecture](GRINDER_ARCHITECTURE.md).
2. Inspect the proposed [G001 cycle manifest](cycles/G001-v035-live-verification/CYCLE_MANIFEST.md).
3. Run [the launch checklist](cycles/G001-v035-live-verification/LAUNCH_CHECKLIST.md).
4. Copy the one-line worker prompts from
   [G001 copy-paste prompts](cycles/G001-v035-live-verification/COPY_PASTE_PROMPTS.md).
5. Each prompt directs its Codex instance to exactly one lane brief:
   - [Lane A — acceptance core](cycles/G001-v035-live-verification/LANE_A_ACCEPTANCE_CORE.md)
   - [Lane B — Hython tiers and fixtures](cycles/G001-v035-live-verification/LANE_B_HYTHON_TIERS.md)
   - [Lane C — compatibility and baselines](cycles/G001-v035-live-verification/LANE_C_COMPATIBILITY_BASELINES.md)
   - [Lane D — runner governance](cycles/G001-v035-live-verification/LANE_D_RUNNER_GOVERNANCE.md)
6. After the four lanes have reviewable commits, give a fresh instance the
   [integration-captain brief](cycles/G001-v035-live-verification/INTEGRATION_CAPTAIN.md).

## Dispatch rule

Every cycle begins as `PROPOSED`. Do not launch its lane briefs until the human owner explicitly
accepts the named cycle. For G001, the exact launch phrase is:

> Accept Grinder Cycle G001 and launch lanes A-D from v0.30.0.

Acceptance freezes the manifest's base commit, lane boundaries, and required gates. Any material
scope change after launch becomes a recorded manifest amendment or a later cycle—not an informal
instruction delivered to only one lane.

## Reusable files

- [Lane instruction template](templates/LANE_INSTRUCTIONS_TEMPLATE.md)
- [Lane receipt template](templates/LANE_RECEIPT_TEMPLATE.md)
