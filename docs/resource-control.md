# Cook, observation, and validation

Milestone 3 makes cooking an explicit resource decision and separates three concerns:

1. a cook job declares what Houdini may compute;
2. structural validation reads only an already-cooked result;
3. visual observation creates an explicit artifact without relying on selection or the active
   pane.

## Cook job lifecycle

`cook.job.submit` requires:

- an absolute Houdini `node_path`;
- one scope: `single_node`, `display_chain`, `one_frame`, or `frame_range`;
- a finite estimate for points, primitives, memory bytes, and seconds;
- the command policy ceilings for those same dimensions and `max_frames`;
- an allowlisted JSONL `log_path`;
- an explicit `frame` only for `one_frame`;
- an inclusive `[start, end, step]` only for `frame_range`, expanded at submission and bounded by
  `max_frames`;
- an explicit `force` choice.

Submission does not cook. It stores the exact policy and target node session ID, preventing a
deleted/replaced node from inheriting a queued job. Use `cook.job.run`, `cook.job.cancel`, and
`cook.job.status` for the lifecycle. `cook.node` is a convenience that submits and immediately
runs the same contract.

```json
{
  "tool": "cook.job.submit",
  "arguments": {
    "node_path": "/obj/HERMES_RELIC/OUT_RELIC",
    "scope": "display_chain",
    "force": false,
    "estimate": {
      "points": 250000,
      "primitives": 250000,
      "memory_bytes": 268435456,
      "seconds": 12.0
    },
    "log_path": "/project/.hermes/cooks.jsonl"
  },
  "policy": {
    "max_points": 500000,
    "max_primitives": 500000,
    "max_memory_bytes": 536870912,
    "max_seconds": 20.0,
    "max_frames": 1
  }
}
```

If a clean cached output already exceeds policy, the job is blocked before `node.cook`. Dirty
outputs are checked against their declaration before execution and against observed metrics
afterward. Results report elapsed time, points, primitives, vertices, memory, frame, force mode,
node messages, and—when requested—the last SOP cook path.

Houdini native cooks are wrapped in `hou.InterruptableOperation` with the policy timeout. This is
cooperative: Houdini must update progress internally for an in-flight native cook to notice the
timeout. Pending cancellation is strict; in-flight termination is not a process kill. Long or
untrusted simulations belong in a future isolated background-job stage.

Every transition is appended and flushed to `hermes.houdini.cook_job` JSONL provenance.

For `frame_range`, Houdini evaluates the expanded frames in order under one total timeout. The
result includes metrics and elapsed time for every frame, reports peak topology/memory against the
policy, associates errors and warnings with their frame, and restores the original global frame.
This is the supported controller for stateful SOP simulations; a stateful range must not be
represented as a nominal `one_frame` request.

## Structural validation

`geometry.metrics` refuses dirty nodes instead of causing an implicit cook. Once a job succeeds,
`geometry.validate` can enforce:

- point and primitive count ranges;
- required point/primitive attributes and groups;
- finite bounds;
- a no-errors/no-unapproved-warnings contract.

This keeps validation read-only and makes the cook that produced its data attributable.

## Visual observation

`graph.capture_svg` renders a deterministic, headless SVG from node positions, connections,
operator types, output contracts, and Hermes metadata. It never changes selection, current node,
pane path, or display flags and caps capture size at 500 nodes by default.

`graph.capture_manifest` writes the same selection-free graph state as structured JSON, plus an
allowlisted set of public parameter values, caller metadata, and metrics from explicitly named
already-clean SOP nodes. It never cooks implicitly, rejects non-finite/oversized metadata, and
uses the same no-overwrite output policy. `hip.save_snapshot` complements the pre-edit checkpoint
with an incremented final `.hipnc` artifact while restoring the in-memory scene name afterward.

`observation.viewers` lists stable GUI pane and viewport names. `viewport.capture` then requires
all of the following:

- exact viewer and viewport names;
- an absolute camera node path;
- one integer frame;
- one literal PNG output path inside an approved root;
- a resolution at or below both the command budget and the conservative Apprentice ceiling of
  1280×720.

The tool copies flipbook settings instead of changing the interactive defaults, captures through
the explicit camera, and restores the prior viewport camera afterward. It fails in hython rather
than silently falling back to active UI state.

Sprint 8 adds a separate Karma CPU preview controller. `solaris.karma_rop.build` configures but
does not execute an editable USD Render ROP. `render.karma.preview` then requires exact approval,
explicit external-process consent, one frame, a non-existing `.png`/`.exr` path, an Apprentice-safe
resolution, a time limit, maximum threads, and output-byte budget. It verifies the artifact after
the external `husk` process exits. Multi-frame renders and flipbooks remain outside this contract.
