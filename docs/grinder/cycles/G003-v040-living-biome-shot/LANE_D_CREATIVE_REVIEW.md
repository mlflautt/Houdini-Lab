# Grinder Lane G003-D — Creative Review and Continuation

## Mission

Implement the Houdini-independent review contract that packages authentic artifacts without ranking
them, binds exact owner feedback to exact bytes and candidate IDs, converts that feedback into
explicit bounded revision hypotheses, and hands the work to another agent without laundering
project-local taste into universal rules.

## Frozen execution contract

- Worktree: `/Users/m1/houdini-g003-d`
- Branch: `codex/grinder-g003-d-creative-review`
- Base: exact protected-main accepted SHA in the launch record
- Other-lane dependencies: none; plain mappings and portable artifact records only
- Merge authority: integration captain only

Stop unless Gate V/H1 and the launch record are complete, HEAD/base are exact, and the tree is clean.
Read root instructions, architecture, verification ladder, local critic boundaries, existing
handoff/observer schemas, accepted packet, audition receipt, and this brief.

## Owned paths

- `hermes_houdini/creative_review.py`
- `tests/unit/test_creative_review.py`
- `tests/fixtures/projects/g003-review-*.json`
- `docs/creative-review.md`
- `docs/grinder/receipts/G003-D.md`

Do not edit recipes, skills, project fixtures, compiler/observer/runtime, shared metadata, workflows,
another receipt, or any artifact bytes.

## Required pure API

Expose equivalent plain-mapping semantics:

```text
build_review_packet(project, *, candidates, artifacts, mechanics, presentation_order) -> dict
bind_human_feedback(packet, *, artifact_hashes, candidate_ids, verbatim, decisions=()) -> dict
plan_revision_hypotheses(review, *, allowed_levers, ceilings) -> dict
build_creative_handoff(review, *, project_root) -> dict
creative_review_sha256(document) -> str
```

Bind live-byte SHA-256, portable relative paths, capability/variant IDs, frame spans, camera/render
identity, stable order, and evidence status. Missing or mismatched bytes block review claims. Human
feedback is append-only and verbatim. Revision hypotheses name bounded graph, parameter, timing,
material, light, atmosphere, or camera changes; each includes evidence, uncertainty, expected visual
effect, budget, rollback, and new approval need. Hypotheses never execute or become taste facts.

Mechanical reports may reject corrupt/blank/duplicate/cropped evidence only. They cannot fill
ratings, preference, originality, mood, winner, selection, or why. The handoff separates project
taste notes from reusable mechanical knowledge and states liked, disliked, rejected, changed, and
unjudged items explicitly.

## Verification and handoff

Test stable hashes/order, byte mismatch/missing/traversal/symlink rejection, exact feedback binding,
null unreviewed fields, rejected lineage, contradictory feedback preservation, allowed-lever and
budget enforcement, portable roots, no aesthetic inference, and clean import without Houdini.
Run targeted/full pure, Ruff, diff/ownership checks. Live/Hython/pixel/human evidence is not produced
by this lane.

Commit owned paths and receipt, push, and open an unmerged PR. Report exact base/head, APIs, tests,
fixtures, assumptions, and integration requirements without inventing user guidance.
