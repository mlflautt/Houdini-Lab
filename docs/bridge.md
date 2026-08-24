# Persistent bridge and approvals

The Milestone 1 bridge keeps all HOM mutations on Houdini's main event loop while allowing
Hermes to send bounded commands from a separate local process.

```text
Hermes client
  -> signed HTTP request on 127.0.0.1:8765
  -> outside bridge validates protocol, size, signature, and request id
  -> signed length-prefixed frame on 127.0.0.1:8766
  -> Houdini listener thread authenticates and enqueues plain data
  -> hou.ui event-loop callback executes at most four commands per pump
  -> signed structured result returns through the same path
```

Both listeners reject non-loopback hosts. Frames are limited to 1 MiB. Interactive request
ids are mandatory and retained briefly after completion, so accidental retries are rejected
instead of executing twice. A request that times out before event-loop execution is cancelled
and will not mutate the scene later.

## Starting a session

Generate one secret per working session and make it available to both Houdini and the
outside bridge:

```bash
export HERMES_HOUDINI_BRIDGE_SECRET="$(python -c 'from bridge.auth import make_secret; print(make_secret())')"
# Start Houdini from this environment, then:
python -m bridge.server --mode interactive --port 8765 --houdini-port 8766
python -m bridge.client --tool system.capabilities
```

The Houdini startup script stores the live handle at `hou.session.hermes_runtime`. If startup
fails, inspect `hou.session.hermes_runtime_error` in Houdini's Python shell. Override the
inside port with `HERMES_HOUDINI_INTERNAL_PORT`; both sides must use the same value.

Filesystem-writing tools fail closed until approved roots are configured. Supply one or more
absolute roots, separated with the platform path separator (`:` on macOS):

```bash
export HERMES_HOUDINI_ALLOWED_ROOTS="$PWD/projects:$PWD/.hermes"
```

The startup script resolves these roots and passes them to the dispatcher. Checkpoint, replay,
cache, and output paths are resolved through the same policy, including symlinks.

For an isolated command that must not touch the open scene:

```bash
python -m bridge.server --mode hython --hython /absolute/path/to/hython
```

Each headless request gets a fresh Houdini session; approval/resume therefore belongs to
interactive mode.

## Explicit approvals

Read-only and low-risk commands execute immediately. Medium-risk commands return `blocked`
with a short-lived, opaque `approval_id` and do not mutate the graph.

```bash
python -m bridge.client --tool node.connect --args '{"from_path":"/obj/A/SRC","to_path":"/obj/A/OUT"}'
python -m bridge.client --list-approvals
python -m bridge.client --approve APPROVAL_ID
# or
python -m bridge.client --deny APPROVAL_ID
```

Approval grants are single-use and execute the exact stored envelope; arguments cannot be
changed between review and execution. Expired, denied, consumed, or unknown ids fail closed.
High-risk/arbitrary-code commands remain blocked by safe mode even before approval.

## Current boundary

The bridge provides persistent transport, authentication, request replay protection,
structured errors, and exact-envelope approval resume. Transactional multi-command graph
batches, checkpoints, rollback, and replay records are implemented by the graph kernel; see
[`graph-kernel.md`](graph-kernel.md). Cook jobs can be cancelled while pending and expose
explicit status/results. An in-flight native Houdini cook uses Houdini's cooperative interrupt
and timeout mechanism; it cannot be treated as a hard process kill. See
[`resource-control.md`](resource-control.md).
