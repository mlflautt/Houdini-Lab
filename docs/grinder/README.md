# Houdini Lab Grinder

The Grinder is the repository's development control plane. It converts the grand roadmap into
bounded, parallel cycles that independent Codex instances can execute without sharing hidden
conversation state.

It is deliberately separate from the Hermes/Houdini runtime control plane. The runtime controls
Houdini work; the Grinder controls how this repository is changed.

## Start here

1. Read [the Grinder architecture](GRINDER_ARCHITECTURE.md).
2. Review the verified-candidate
   [G002 project-compiler manifest](cycles/G002-v040-project-compiler/CYCLE_MANIFEST.md).
3. Verify frozen tag `v0.35.0` resolves to the exact G002 base commit before dispatch.
4. Use the
   [G002 launch checklist](cycles/G002-v040-project-compiler/LAUNCH_CHECKLIST.md) and paste the
   [one-line worker prompts](cycles/G002-v040-project-compiler/COPY_PASTE_PROMPTS.md).
5. Review the [G003 Living Biome outline](cycles/G003-v040-living-biome-shot/PROPOSAL.md). It remains
   non-dispatchable until G002 merges and the owner chooses a motion direction.

## Cycle history

- [G001 — v0.35 live verification](cycles/G001-v035-live-verification/CYCLE_MANIFEST.md): released
  as `v0.35.0`; technical evidence lives in `docs/grinder/receipts/G001-I.md`.
- [G002 — project compiler kernel](cycles/G002-v040-project-compiler/CYCLE_MANIFEST.md): verified
  integration candidate; protected-main PR pending.
- [G003 — Living Biome Shot](cycles/G003-v040-living-biome-shot/PROPOSAL.md): outline awaiting the
  exact merged G002 base and an owner-owned motion choice.

## Dispatch rule

Every cycle begins as `PROPOSED`. Do not launch its lane briefs until the human owner explicitly
accepts the named cycle. The manifest supplies the exact phrase only after its base is immutable.
G001 used:

> Accept Grinder Cycle G001 and launch lanes A-D from v0.30.0.

Acceptance freezes the manifest's base commit, lane boundaries, and required gates. Any material
scope change after launch becomes a recorded manifest amendment or a later cycle—not an informal
instruction delivered to only one lane.

## Reusable files

- [Lane instruction template](templates/LANE_INSTRUCTIONS_TEMPLATE.md)
- [Lane receipt template](templates/LANE_RECEIPT_TEMPLATE.md)
