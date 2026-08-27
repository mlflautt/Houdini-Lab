# Houdini Lab Grinder

The Grinder is the repository's development control plane. It converts the grand roadmap into
bounded, parallel cycles that independent Codex instances can execute without sharing hidden
conversation state.

It is deliberately separate from the Hermes/Houdini runtime control plane. The runtime controls
Houdini work; the Grinder controls how this repository is changed.

## Start here

1. Read [the Grinder architecture](GRINDER_ARCHITECTURE.md).
2. Treat the verified
   [G002 project-compiler manifest](cycles/G002-v040-project-compiler/CYCLE_MANIFEST.md) as the
   current composition-contract baseline.
3. Review the proposed creative-first
   [G003 Living Biome manifest](cycles/G003-v040-living-biome-shot/CYCLE_MANIFEST.md).
4. Accept and run the bounded
   [three-way visual audition](cycles/G003-v040-living-biome-shot/VISUAL_AUDITION.md); the operator
   stops for exact live/render authority before producing pixels.
5. After viewing all three authentic motion studies, record the owner-owned
   [continuation decision](cycles/G003-v040-living-biome-shot/MOTION_DECISION.md).
6. Only after that reviewed decision and explicit lane acceptance, use the
   [G003 launch checklist](cycles/G003-v040-living-biome-shot/LAUNCH_CHECKLIST.md) and
   [one-line worker prompts](cycles/G003-v040-living-biome-shot/COPY_PASTE_PROMPTS.md).

## Cycle history

- [G001 — v0.35 live verification](cycles/G001-v035-live-verification/CYCLE_MANIFEST.md): released
  as `v0.35.0`; technical evidence lives in `docs/grinder/receipts/G001-I.md`.
- [G002 — project compiler kernel](cycles/G002-v040-project-compiler/CYCLE_MANIFEST.md): verified and
  merged through protected main at `44727325ecb5262a613d259d6db2ff23274ed211`.
- [G003 — Creative-First Living Biome](cycles/G003-v040-living-biome-shot/CYCLE_MANIFEST.md): proposed
  visible vertical slice; begins with three authentic motion auditions, then creative-discipline
  lanes, an integrated animated comparison, owner critique, and one preserved revision.

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
