# Hermes Houdini v0.30 Operator Runbook

This is the compact entry path for Hermes, Codex, or a medium local agent. The agent should operate
registered capabilities, not synthesize a repository-wide HOM script.

## Operating loop

1. Call `session.describe`. Do not inspect geometry, move the frame, or cook to learn the session.
2. Call `system.catalog` with the narrowest known context, license, build, risk, and dependency
   filters. If no registered capability fits, stop and propose a capability addition.
3. Call `intent.plan.create`. Keep all plausible creative alternatives, declare costs and approvals,
   and leave `winner: null`.
4. Show the plan before medium, high, external, render, simulation, overwrite, or publication work.
5. Execute registered calls in plan order. Grant only the exact approval ID returned by the
   dispatcher. Never treat approval as reusable.
6. Cook only the declared node, scope, frame range, and budget.
7. Verify graph, cooked data, and authentic viewport/Karma pixels as separate evidence rungs. Mark
   unavailable rungs `pending`, `warn`, or `blocked`; do not infer them from another rung.
8. Preserve candidate branches, empty rating slots, rejected lineage, and exact human wording.
9. Call `handoff.create` inside the approved project root. Include the final `.hipnc`, replay logs,
   stable Hermes IDs, artifacts, hashes, evidence states, warnings, human feedback, and pending gates.
10. In a fresh process, call `handoff.inspect`, then `handoff.resume_plan`. Review the dry plan before
    loading its checkpoint or executing any refinement.

## Required invariants

- Native node graph first; HOM only orchestrates.
- Absolute node paths and stable `hermes_id` values; no selection or current-pane dependency.
- New branch, Switch, Null contract, checkpoint, and bypass before destructive replacement.
- Apprentice outputs remain non-commercial: `.hipnc`/`.hdanc`, watermarked render, conservative
  `1280x720` ceiling, Karma CPU, no Engine export, no third-party renderer.
- Catalog relevance and safety may be filtered. Aesthetic quality may not be auto-ranked.
- `handoff.resume_plan` never executes automatically.

## Minimal agent prompts

Bootstrap:

> Describe the Houdini session without cooking. Filter the catalog to the live build, license, and
> relevant context. Report missing dependencies and active approvals before proposing work.

Plan:

> Convert this brief into an intent plan using registered capabilities. Preserve alternatives,
> estimate seconds, memory, frames, and output bytes, name each approval, and route graph/data/visual
> verification separately. Do not select an aesthetic winner.

Execute:

> Execute only the approved plan in a checkpointed graph transaction. Use the declared cook scope,
> collect structured metrics, and capture authentic visual proof. Stop on a failed evidence rung.

Handoff:

> Record the final checkpoint, replay logs, stable IDs, artifact hashes, exact feedback, rejected or
> retained alternatives, warnings, and pending human gates. Validate the handoff, then produce a dry
> fresh-session resume plan without executing it.

## Reference acceptance

From the repository root, use an unused absolute artifact path:

```bash
HYTHON=/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython

"$HYTHON" scripts/run_v030_acceptance.py \
  --mode execute \
  --artifact-dir /absolute/disposable/v030-acceptance \
  --render

"$HYTHON" scripts/run_v030_acceptance.py \
  --mode resume \
  --artifact-dir /absolute/disposable/v030-acceptance \
  --load-checkpoint
```

The two commands must run in separate Hython processes. The first process builds
`model.fractal_relic`, optionally composes a bounded Karma proof, and writes a hashed handoff. The
second validates compatibility and artifact hashes, loads the checkpoint only because the operator
explicitly passed `--load-checkpoint`, resolves stable IDs, and records that no refinement was
automatically executed.

Omit `--render` only for structural development. That leaves visual evidence `pending` and is not a
release acceptance. If no human feedback was supplied, the feedback record also remains `pending`;
the harness never invents taste evidence.

## Failure handling

- Empty catalog result: widen one filter at a time; do not invent unregistered arbitrary code.
- Build or package drift: retain the handoff, report the exact mismatch, and do not replay.
- Changed or missing artifact hash: mark evidence invalid and locate an immutable source artifact.
- Missing visual proof: run a named viewport capture or bounded Karma render; structural success is
  insufficient.
- Human review absent: preserve blank ratings and keep the release or aesthetic decision pending.
