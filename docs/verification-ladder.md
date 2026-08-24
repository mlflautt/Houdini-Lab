# Verification ladder

Hermes should ask a human to judge taste, not to discover black frames, missing geometry, stale
parameters, or a graph that no longer matches its render. Verification therefore escalates from
cheap deterministic evidence to increasingly interpretive model critique. Every rung is advisory
until an explicit policy gate says otherwise; none may silently select a creative winner.

## 1. Structural and temporal contracts

This is the required first gate. Validate exact node category/type, stable roles and IDs, connection
order, public controls, seed/lineage, expected attributes, finite geometry, Houdini messages, frame
restoration, and cook budgets. Temporal skills record per-frame topology/bounds/memory/time rather
than proving only the last frame. A failed contract blocks later aesthetic interpretation because a
vision model should not rationalize a broken graph.

Sprint 12 is the first full temporal example. `motion.calligraphy.validate` checks every requested
integer frame, all three Particle Trail branches, scalar `id`/`age`/`life`, peak trail points, final
candidate distinctness, human Switch equivalence, fixed comparison order, and the named Houdini 22
half-frame compatibility boundary.

## 2. Deterministic image mechanics

`visual.analyze@1.0.0` decodes non-interlaced 8-bit PNG files without third-party dependencies. It
records hashes, dimensions, luminance mean/deviation, black and white fractions, subject occupancy
and bounding box, 32-bin entropy, edge density, expected comparison-panel occupancy, likely crop,
and exact duplicates. Blank/crushed/blown evidence fails; low contrast, tiny subjects, crop risk,
or missing panels warn. These are mechanical diagnostics, not composition scores.

Before trusting the thresholds broadly, maintain a small calibration corpus containing known-good
captures plus deliberately black, white, clipped, tiny, duplicate, and missing-panel fixtures. Run
that corpus when changing decoding or thresholds. Rendered evidence remains authoritative when a
Houdini parameter reports a plausible value but the pixels disagree.

Sprint 12 acceptance exercised this feedback loop rather than treating the first render as proof.
The analyzer rejected the sparse first pass, and visual review exposed that a one-pixel crop test
was too permissive. The production threshold now reserves a two-percent image-border safety margin;
the final framing passed the stricter gate. Apprentice watermarks can still create false foreground
inside the lower-right panel, so clean viewport captures are preferred for panel-presence checks and
the critique rubric must explicitly inspect watermark overlap on Karma evidence.

## 3. Local vision-language critique

Local inference is preferred because renders, graphs, and source remain on the workstation. No model
is downloaded or started implicitly. On the current 64 GB Apple-silicon target, the recommended
first critic is [Qwen3-VL 8B through Ollama](https://ollama.com/library/qwen3-vl); the official
library lists vision-capable 2B, 4B, 8B, 30B, and 32B variants. Use 8B for routine triage and a 30B
variant only for disputed or subtle cases. [MLX-VLM](https://github.com/Blaizzy/mlx-vlm) is the
Apple-silicon-native alternative when its model/server workflow offers a measurable benefit.

The local critic receives a `verification.critique.package@1.0.0` artifact, not an untracked folder.
The packet hashes the exact image, graph SVG, structural validation, graph manifest, deterministic
visual report, recipe, skill, and validator code. Its rubric asks for evidence-linked mechanical
status, subject readability, composition/crop, candidate distinctness, whether graph intent matches
the image, uncertainties, and bounded next edits. Responses must be structured JSON and record
model/version, prompt hash, artifact hashes, runtime, and raw response hash.

Model reliability is itself tested against the calibration corpus. A model that misses known black,
clipped, duplicate, or absent-panel cases cannot reduce human review. Local VLM judgments are marked
`available_unverified` until that evaluation passes. Scores may be stored as advisory fields but
must never fill `winner` or `human_rating`.

Host audit on 2026-08-22 found Ollama 0.32.9 installed but no running daemon or installed vision
model. Sprint 12 therefore stops at the hashed handoff packet: model inference remains
`available_unverified`, and no model download is implied by building or validating the skill.

## 4. External omnimodal critique

An external critic is an optional escalation when local models disagree, are unavailable, or lack
the needed spatial/code reasoning. It is a separate `external` operation requiring explicit network
approval. Send the minimum hashed packet, exclude scenes/assets not required by the rubric, scan code
and manifests for secrets or unrelated paths, and record provider/model/request/response provenance.
The response remains advisory; external confidence does not become execution authority.

## 5. Human review triggers

Human attention is reserved for final taste, ambiguous intent, policy exceptions, structural-versus-
pixel disagreement, conflicting critics, or low-confidence suggestions with material consequences.
The agent may automatically repair deterministic failures inside an already authorized task, then
re-run the ladder. It may not auto-accept an aesthetic winner. Comparisons preserve stable candidate
IDs, lineage, empty ratings, and all alternatives.

## Rollout sequence

1. Sprint 12: structural validator, deterministic PNG analyzer, hashed critique packet, calibration
   fixtures, and optional capture integration.
2. Next verification increment: approved local Ollama adapter with an allowlisted vision model,
   schema validation, time/memory limits, and calibration scoring. Default remains off.
3. Later: consensus/escalation policy across deterministic checks, one local critic, and optionally
   one external critic; human review only on defined triggers.
4. Long term: project-specific aesthetic rubrics learned from explicit human ratings without
   changing the invariant that the human remains the final creative authority.
