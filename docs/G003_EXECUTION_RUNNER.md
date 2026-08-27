# G003 Approved-Manifest Execution Runner

This is the portable live-operation seam for Codex, Hermes Agent, OpenCode, DeepSeek harnesses, and
small local agents. The harness does not synthesize HOM or replay conversation context. It validates
one canonical manifest, then asks the repository dispatcher to execute only the exact registered
envelopes stored in that manifest.

## Authority boundary

Repository architecture work—code, tests, docs, manifests, branches, commits, and PR maintenance—is
ordinary development. Gate V authority is required only when the runner will create or change a
Houdini scene, cook, save, launch Karma/husk or ffmpeg, or write the approved live artifact root.

An approval applies to one canonical manifest hash and one initially absent artifact root. It is
single-use. A stopped root is immutable evidence: fix the architecture, generate a new manifest
with a new root, and obtain authority for that new subject. Never resume by deleting, editing, or
overwriting a failed attempt.

## Two-layer design

`hermes_houdini.g003_execution` is Houdini-free. Any Python 3.11+ harness can import it to:

- verify the canonical approval-subject hash;
- enforce the exact three-method presentation order, 115 registered calls, 36 render calls, and
  sampled-frame order;
- reject network, arbitrary-code, overwrite, external-process, path, ranking, or human-field drift;
- verify that every durable path is confined to the approved artifact root; and
- generate the neutral labels and script-free portable review page.

`scripts/run_g003_visual_audition.py` is the thin Hython operator. It additionally verifies the
clean branch and accepted-base ancestry, fresh untitled scene, exact Houdini build and Apprentice
license, package skiplist, and ffmpeg build. Each medium/external envelope first enters the normal
dispatcher approval store and is then granted by its single-use approval ID. The runner never calls
an unregistered Houdini graph tool.

The runner restores the frame after every envelope, checks `CANCEL` between calls, records every
request/result/approval/frame transition as JSONL, enforces aggregate time/memory/byte ceilings,
refuses existing outputs, and leaves creative selection fields null.

Stateful SOP sources never rely on a prior command's cache. Stage validation and each sparse render
declare the exact source SOP, warm-up start, target frame, and frame budget; the registered tools
sequentially replay that range, invalidate the matching SOP Import LOP, and restore the caller's
frame. The Houdini-free validator rejects any source-path or warm-up-budget drift.

## Harness procedure

From the dedicated clean worktree:

1. Read `AGENTS.md`, `docs/architecture.md`, `docs/CREATIVE_AGENT_START_HERE.md`, the Gate V receipt,
   and the exact manifest.
2. Independently compute and compare the manifest subject. Confirm the artifact root does not
   exist. Run the command below with `--preflight-only`; it validates Git, Houdini, dispatcher, and
   ffmpeg state and exits without creating the root or requiring an approval note.
3. Confirm the human/operator authorization names that exact subject and scope. Preserve the exact
   wording in `--approval-note`; do not paraphrase it into broader authority.
4. Start one Hython process. Apprentice is node-locked, so do not run a second Hython job in
   parallel.
5. Stream the JSON event output. To cancel, create `<artifact-root>/CANCEL`; the runner stops before
   the next envelope and preserves completed evidence.
6. On success, inspect `manifests/g003_v_execution_receipt.json`, all three visual-verification
   reports, scene snapshots, and the static review index. Present all methods without ranking and
   stop for human review.
7. On failure, preserve the root and use its JSONL receipt and checkpoints for diagnosis. Any retry
   requires a freshly generated manifest/root.

## Live command

Substitute only values copied from the exact approved manifest/record:

```bash
env HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json PYTHONPATH=. \
  /Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython \
  scripts/run_g003_visual_audition.py \
  --manifest '/absolute/project-confined/manifest.json' \
  --approved-manifest-sha256 '<64-hex canonical subject>' \
  --approval-note '<exact owner or operator wording>'
```

Do not add shell pipes, redirections, environment packages, plugin paths, or alternate executables.
The command emits JSON lines to standard output; the durable project-confined JSONL is authoritative.

For the mutation-free readiness check, use the same command with `--preflight-only` and omit
`--approval-note`.

## Evidence separation

- Graph evidence: checkpoints, replay logs, graph SVGs/manifests, stable Hermes IDs.
- Data evidence: registered capability validations and bounded cook metrics.
- Pixel/motion evidence: exact Karma PNGs and deterministic sequence analysis.
- Presentation evidence: local MP4 previews, contact sheet, labels, and static HTML.
- Human evidence: remains null until the owner reviews exact artifact hashes.

Mechanical warnings never become aesthetic rankings. A technically passing execution does not
select a Living Biome motion vocabulary or authorize downstream G003 lanes.
