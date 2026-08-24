# Transactional graph kernel

Milestone 2 adds one medium-risk operation, `graph.apply_batch`, for bounded multi-node graph
edits. It is graph-first: the operations create and wire native nodes; no Python, VEX, cook,
delete, rename, file-load, or render operation can be embedded in a batch.

## Transaction contract

Before mutation, the kernel validates the complete JSON batch, resolves absolute Houdini paths,
checks exact operator types, rejects a previously applied `batch_id`, snapshots the affected
networks, and saves an incremented non-commercial checkpoint. The edit then runs in one Houdini
undo group.

On success it returns:

- stable `hermes_id`, `hermes_role`, `hermes_created_by`, and `hermes_batch_id` metadata;
- exact resolved changes and a before/after graph diff;
- the checkpoint and append-only JSONL replay-log paths;
- changed-node records suitable for a Hermes/Houdini handoff.

On failure, in-memory compensation restores connections, scalar parameter values, comments,
display/render/bypass flags (including mutually exclusive sibling flags), and destroys only
nodes created by the batch. If that compensation itself fails, the durable checkpoint is loaded.
Both successful and rolled-back attempts get provenance records.

Literal parameter edits refuse parameters with expressions or keyframes. This prevents a batch
from silently destroying authored animation; a future explicit animation operation can provide
the richer contract needed to edit those safely.

## Allowed operations

The batch is capped at 200 operations. References are local to the batch, unique, and must be
declared by an earlier `create` operation.

| Operation | Purpose |
|---|---|
| `create` | Create an exact native operator under an absolute parent path and tag it. |
| `connect` | Connect a prior ref or absolute node path to another ref/path. |
| `set_parameter` | Set one scalar, unanimated parameter. |
| `set_flags` | Set display, render, and/or bypass flags. |
| `set_comment` | Add an artist-readable node comment. |

Example command arguments:

```json
{
  "batch_id": "relic.blockout-01",
  "checkpoint_dir": "/project/.hermes/checkpoints",
  "log_path": "/project/.hermes/replay/graph.jsonl",
  "operations": [
    {
      "op": "create",
      "ref": "src",
      "parent_path": "/obj/HERMES_RELIC",
      "operator_type": "sphere",
      "name": "SRC_RELIC",
      "category": "Sop",
      "role": "source",
      "parameters": {"radx": 1.25}
    },
    {
      "op": "create",
      "ref": "out",
      "parent_path": "/obj/HERMES_RELIC",
      "operator_type": "null",
      "name": "OUT_RELIC",
      "category": "Sop",
      "role": "output"
    },
    {"op": "connect", "from": "src", "to": "out"},
    {"op": "set_comment", "target": "out", "comment": "Editable output contract"},
    {"op": "set_flags", "target": "out", "display": true, "render": true}
  ]
}
```

`checkpoint_dir` and `log_path` must be inside a root declared by
`HERMES_HOUDINI_ALLOWED_ROOTS`. The first request returns `blocked` with an approval id. Granting
that id executes the exact stored envelope once; changing the batch requires a new request and
approval.

## Replay and idempotency

The JSONL record stores protocol request data, operations, resolved changes, graph diff, Houdini
build/license, checkpoint, status, and rollback diagnostics. Replaying its `operations` with the
same `batch_id` in a clean scene produces the same stable Hermes IDs. Reusing a `batch_id` while
managed nodes from that batch remain in the scene is rejected, preventing accidental duplicate
execution.

Replay recreates intent and graph structure; it does not cook geometry. Data and visual
verification remain explicit later steps in the agent loop.
