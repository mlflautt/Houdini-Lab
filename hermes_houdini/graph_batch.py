"""Checkpointed, replayable graph-edit batches.

The public validator is pure Python.  HOM is used only by :func:`apply_batch`,
which must run on Houdini's main/event-loop thread.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

from . import get_hou
from .execution import current_envelope
from .expressions import validate_hscript_expression
from .graph_state import _json_value, diff_snapshots, snapshot_networks
from .ids import make_id
from .schemas.command import ChangedNode, Status, ToolResult
from .transactions import restore_checkpoint, save_checkpoint
from .validation import node_type_exists

MAX_BATCH_OPERATIONS = 200
BATCH_SCHEMA_VERSION = "1.0"
_BATCH_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}\Z")
_REF = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
_CHECKPOINT_STEM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_COMMON_KEYS = {"op"}
_OP_KEYS = {
    "create": _COMMON_KEYS
    | {
        "ref",
        "parent_path",
        "operator_type",
        "name",
        "category",
        "role",
        "parameters",
        "expressions",
        "comment",
        "position",
        "exact_name",
    },
    "connect": _COMMON_KEYS
    | {
        "from",
        "to",
        "input_index",
        "output_index",
    },
    "set_parameter": _COMMON_KEYS | {"target", "name", "value"},
    "set_flags": _COMMON_KEYS | {"target", "display", "render", "bypass"},
    "set_comment": _COMMON_KEYS | {"target", "comment"},
}


def _require_string(value: Any, label: str, *, absolute: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    if absolute and not value.startswith("/"):
        raise ValueError(f"{label} must be an absolute Houdini path")
    return value


def _validate_target(value: Any, label: str, refs: set[str]) -> str:
    target = _require_string(value, label)
    if target.startswith("/"):
        return target
    if target not in refs:
        raise ValueError(f"{label} references unknown or later ref: {target}")
    return target


def validate_batch(batch_id: str, operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and JSON-normalize an allowlisted graph batch."""
    if not isinstance(batch_id, str) or not _BATCH_ID.fullmatch(batch_id):
        raise ValueError("batch_id must be 1-80 safe identifier characters")
    if not isinstance(operations, list) or not operations:
        raise ValueError("operations must be a non-empty list")
    if len(operations) > MAX_BATCH_OPERATIONS:
        raise ValueError(f"batch exceeds {MAX_BATCH_OPERATIONS} operations")
    try:
        normalized = json.loads(json.dumps(operations, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"operations must be finite JSON data: {exc}") from exc

    refs: set[str] = set()
    for index, operation in enumerate(normalized):
        prefix = f"operations[{index}]"
        if not isinstance(operation, dict):
            raise ValueError(f"{prefix} must be an object")
        op = operation.get("op")
        if op not in _OP_KEYS:
            raise ValueError(f"{prefix}.op is not allowed: {op!r}")
        unknown = set(operation) - _OP_KEYS[op]
        if unknown:
            raise ValueError(f"{prefix} has unknown keys: {', '.join(sorted(unknown))}")
        if op == "create":
            ref = _require_string(operation.get("ref"), f"{prefix}.ref")
            if not _REF.fullmatch(ref):
                raise ValueError(f"{prefix}.ref is not a safe reference")
            if ref in refs:
                raise ValueError(f"duplicate ref: {ref}")
            _require_string(operation.get("parent_path"), f"{prefix}.parent_path", absolute=True)
            _require_string(operation.get("operator_type"), f"{prefix}.operator_type")
            if "name" in operation and not isinstance(operation["name"], str):
                raise ValueError(f"{prefix}.name must be a string")
            if "exact_name" in operation and not isinstance(operation["exact_name"], bool):
                raise ValueError(f"{prefix}.exact_name must be a boolean")
            if operation.get("exact_name") and not operation.get("name"):
                raise ValueError(f"{prefix}.exact_name requires name")
            if "position" in operation:
                position = operation["position"]
                if (
                    not isinstance(position, list)
                    or len(position) != 2
                    or any(
                        not isinstance(value, (int, float))
                        or isinstance(value, bool)
                        or not math.isfinite(value)
                        for value in position
                    )
                ):
                    raise ValueError(f"{prefix}.position must be two finite numbers")
            if "category" in operation:
                _require_string(operation["category"], f"{prefix}.category")
            for key in ("role", "comment"):
                if key in operation and not isinstance(operation[key], str):
                    raise ValueError(f"{prefix}.{key} must be a string")
            if "parameters" in operation and not isinstance(operation["parameters"], dict):
                raise ValueError(f"{prefix}.parameters must be an object")
            if "parameters" in operation and any(
                not isinstance(name, str) or not name for name in operation["parameters"]
            ):
                raise ValueError(f"{prefix}.parameters keys must be non-empty strings")
            expressions = operation.get("expressions", {})
            if not isinstance(expressions, dict) or any(
                not isinstance(name, str) or not name for name in expressions
            ):
                raise ValueError(f"{prefix}.expressions must be an object with named parameters")
            overlap = set(operation.get("parameters", {})).intersection(expressions)
            if overlap:
                raise ValueError(
                    f"{prefix} parameters cannot be literal and expression: {sorted(overlap)}"
                )
            for name, expression in expressions.items():
                validate_hscript_expression(expression, f"{prefix}.expressions.{name}")
            refs.add(ref)
        elif op == "connect":
            _validate_target(operation.get("from"), f"{prefix}.from", refs)
            _validate_target(operation.get("to"), f"{prefix}.to", refs)
            for key in ("input_index", "output_index"):
                value = operation.get(key, 0)
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ValueError(f"{prefix}.{key} must be a non-negative integer")
        else:
            _validate_target(operation.get("target"), f"{prefix}.target", refs)
            if op == "set_parameter":
                _require_string(operation.get("name"), f"{prefix}.name")
            elif op == "set_flags":
                flags = [key for key in ("display", "render", "bypass") if key in operation]
                if not flags:
                    raise ValueError(f"{prefix} must set at least one flag")
                if any(not isinstance(operation[key], bool) for key in flags):
                    raise ValueError(f"{prefix} flag values must be booleans")
            elif op == "set_comment" and not isinstance(operation.get("comment"), str):
                raise ValueError(f"{prefix}.comment must be a string")
    return normalized


def validate_batch_options(label: str, checkpoint_stem: str) -> None:
    """Validate non-operation options that affect undo metadata and disk paths."""
    if (
        not isinstance(label, str)
        or not label
        or len(label) > 120
        or any(ord(character) < 32 for character in label)
    ):
        raise ValueError("label must be 1-120 printable characters")
    if not isinstance(checkpoint_stem, str) or not _CHECKPOINT_STEM.fullmatch(checkpoint_stem):
        raise ValueError("checkpoint_stem must be a safe 1-64 character filename stem")


def append_replay_record(log_path: str, record: dict[str, Any]) -> None:
    """Append one durable JSONL record; never rewrite existing provenance."""
    parent = os.path.dirname(log_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    line = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
    with open(log_path, "a", encoding="utf-8") as stream:
        stream.write(line + "\n")
        stream.flush()
        os.fsync(stream.fileno())


@dataclass
class _Rollback:
    created: list[Any] = field(default_factory=list)
    connections: list[tuple[Any, int, Any | None, int]] = field(default_factory=list)
    parameters: list[tuple[Any, Any, tuple[Any, ...]]] = field(default_factory=list)
    flags: list[tuple[Any, str, bool]] = field(default_factory=list)
    comments: list[tuple[Any, str]] = field(default_factory=list)

    def restore(self) -> list[str]:
        errors: list[str] = []
        for node, old_comment in reversed(self.comments):
            try:
                node.setComment(old_comment)
            except Exception as exc:
                errors.append(f"comment rollback: {exc}")
        for node, setter_name, old_value in reversed(self.flags):
            try:
                getattr(node, setter_name)(old_value)
            except Exception as exc:
                errors.append(f"flag rollback: {exc}")
        for parm, old_value, old_keyframes in reversed(self.parameters):
            try:
                parm.deleteAllKeyframes()
                if old_keyframes:
                    parm.setKeyframes(old_keyframes)
                else:
                    parm.set(old_value)
            except Exception as exc:
                errors.append(f"parameter rollback: {exc}")
        for node, input_index, old_source, old_output_index in reversed(self.connections):
            try:
                node.setInput(input_index, old_source, old_output_index)
            except Exception as exc:
                errors.append(f"connection rollback: {exc}")
        for node in reversed(self.created):
            try:
                if node.parent() is not None:
                    node.destroy()
            except Exception as exc:
                errors.append(f"created-node rollback: {exc}")
        return errors


def _resolve(target: str, refs: dict[str, Any]) -> Any:
    hou = get_hou()
    node = hou.node(target) if target.startswith("/") else refs.get(target)
    if node is None:
        raise ValueError(f"node not found: {target}")
    return node


def _parent_paths(operations: list[dict[str, Any]]) -> list[str]:
    hou = get_hou()
    paths = {op["parent_path"] for op in operations if op["op"] == "create"}
    for operation in operations:
        for key in ("target", "from", "to"):
            target = operation.get(key)
            if isinstance(target, str) and target.startswith("/"):
                node = hou.node(target)
                if node is None:
                    raise ValueError(f"node not found: {target}")
                paths.add(node.parent().path())
    return sorted(paths)


def _tracked_parameters(operations: list[dict[str, Any]]) -> dict[str, set[str]]:
    tracked: dict[str, set[str]] = {}
    for operation in operations:
        if operation["op"] != "set_parameter":
            continue
        target = operation["target"]
        if target.startswith("/"):
            tracked.setdefault(target, set()).add(operation["name"])
    return tracked


def _preflight(batch_id: str, operations: list[dict[str, Any]]) -> list[str]:
    hou = get_hou()
    parents = _parent_paths(operations)
    for parent_path in parents:
        parent = hou.node(parent_path)
        if parent is None:
            raise ValueError(f"network not found: {parent_path}")
    existing_ids: dict[str, str] = {}
    for node in hou.node("/").allSubChildren():
        if node.userData("hermes_batch_id") == batch_id:
            raise ValueError(f"batch_id already applied at {node.path()}: {batch_id}")
        hermes_id = node.userData("hermes_id")
        if hermes_id:
            existing_ids[hermes_id] = node.path()
    proposed_ids: set[str] = set()
    for operation in operations:
        if operation["op"] == "create":
            category = operation.get("category", "Sop")
            if not node_type_exists(category, operation["operator_type"]):
                raise ValueError(
                    f"operator type {operation['operator_type']} not in category {category}"
                )
            proposed_id = make_id(category, f"{batch_id}:{operation['ref']}")
            if proposed_id in existing_ids:
                raise ValueError(
                    f"stable id already exists at {existing_ids[proposed_id]}: {proposed_id}"
                )
            if proposed_id in proposed_ids:
                raise ValueError(f"stable id collision inside batch: {proposed_id}")
            proposed_ids.add(proposed_id)
    return parents


def _connection_at(node: Any, input_index: int) -> tuple[Any | None, int]:
    for connection in node.inputConnections():
        if connection.inputIndex() == input_index:
            return connection.inputNode(), connection.outputIndex()
    return None, 0


def _set_flag(node: Any, operation: dict[str, Any], rollback: _Rollback) -> None:
    mapping = {
        "display": ("isDisplayFlagSet", "setDisplayFlag"),
        "render": ("isRenderFlagSet", "setRenderFlag"),
        "bypass": ("isBypassed", "bypass"),
    }
    for key, (getter_name, setter_name) in mapping.items():
        if key not in operation:
            continue
        getter = getattr(node, getter_name, None)
        setter = getattr(node, setter_name, None)
        if getter is None or setter is None:
            raise ValueError(f"node {node.path()} does not support {key} flag")
        # Display/render flags are mutually exclusive in common Houdini networks.
        # Capture siblings too, because setting one node can silently change another.
        affected = node.parent().children() if key in {"display", "render"} else (node,)
        for affected_node in affected:
            affected_getter = getattr(affected_node, getter_name, None)
            affected_setter = getattr(affected_node, setter_name, None)
            if affected_getter is not None and affected_setter is not None:
                rollback.flags.append((affected_node, setter_name, bool(affected_getter())))
        setter(operation[key])


def _record_base(
    batch_id: str, operations: list[dict[str, Any]], checkpoint: str
) -> dict[str, Any]:
    hou = get_hou()
    envelope = current_envelope()
    license_name = hou.licenseCategory().name() if hasattr(hou, "licenseCategory") else "unknown"
    return {
        "schema": "hermes.houdini.graph_batch",
        "schema_version": BATCH_SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "batch_id": batch_id,
        "checkpoint": checkpoint,
        "operations": operations,
        "request": envelope.as_dict() if envelope is not None else None,
        "houdini": {"build": hou.applicationVersionString(), "license": license_name},
    }


def apply_batch(
    *,
    batch_id: str,
    operations: list[dict[str, Any]],
    checkpoint_dir: str,
    log_path: str,
    label: str = "Hermes graph batch",
    checkpoint_stem: str = "hermes_graph",
) -> ToolResult:
    """Apply an allowlisted graph batch atomically, with checkpoint and replay log."""
    hou = get_hou()
    validate_batch_options(label, checkpoint_stem)
    normalized = validate_batch(batch_id, operations)
    parents = _preflight(batch_id, normalized)
    tracked_parameters = _tracked_parameters(normalized)
    original_name = hou.hipFile.name()
    checkpoint = save_checkpoint(checkpoint_dir, checkpoint_stem)
    before = snapshot_networks(parents, tracked_parameters)
    rollback = _Rollback()
    refs: dict[str, Any] = {}
    changes: list[dict[str, Any]] = []
    result = ToolResult(status=Status.SUCCESS, checkpoint=checkpoint)
    record = _record_base(batch_id, normalized, checkpoint)

    try:
        with hou.undos.group(label):
            for operation in normalized:
                op = operation["op"]
                if op == "create":
                    parent = hou.node(operation["parent_path"])
                    node = parent.createNode(
                        operation["operator_type"],
                        node_name=operation.get("name") or None,
                        exact_type_name=True,
                    )
                    rollback.created.append(node)
                    if operation.get("exact_name") and node.name() != operation["name"]:
                        raise ValueError(
                            f"requested exact node name {operation['name']!r} but Houdini "
                            f"created {node.name()!r}"
                        )
                    if "position" in operation:
                        node.setPosition(operation["position"])
                    category = operation.get("category", "Sop")
                    actual_category = node.type().category().name()
                    if actual_category != category:
                        raise ValueError(
                            f"created category {actual_category} does not match declared {category}"
                        )
                    hermes_id = make_id(category, f"{batch_id}:{operation['ref']}")
                    node.setUserData("hermes_id", hermes_id)
                    node.setUserData("hermes_role", operation.get("role", ""))
                    node.setUserData("hermes_created_by", "tool:graph.apply_batch@1.0.0")
                    node.setUserData("hermes_manifest_version", "1")
                    node.setUserData("hermes_batch_id", batch_id)
                    node.setComment(operation.get("comment", ""))
                    for name, value in operation.get("parameters", {}).items():
                        parm = node.parm(name)
                        parm_tuple = node.parmTuple(name)
                        if isinstance(value, list) and parm_tuple is not None:
                            if len(value) != len(parm_tuple):
                                raise ValueError(
                                    f"operator {node.type().name()} parameter tuple {name} "
                                    f"requires {len(parm_tuple)} values"
                                )
                            parm_tuple.set(value)
                        elif parm is not None:
                            parm.set(value)
                        elif parm_tuple is not None:
                            parm_tuple.set(value)
                        else:
                            raise ValueError(
                                f"operator {node.type().name()} has no parameter {name}"
                            )
                    for name, expression in operation.get("expressions", {}).items():
                        parm = node.parm(name)
                        if parm is None:
                            raise ValueError(
                                f"operator {node.type().name()} has no scalar parameter {name}"
                            )
                        parm.setExpression(expression, language=hou.exprLanguage.Hscript)
                    refs[operation["ref"]] = node
                    changes.append(
                        {
                            "op": op,
                            "ref": operation["ref"],
                            "path": node.path(),
                            "hermes_id": hermes_id,
                            "type": node.type().name(),
                        }
                    )
                elif op == "connect":
                    source = _resolve(operation["from"], refs)
                    target = _resolve(operation["to"], refs)
                    input_index = operation.get("input_index", 0)
                    output_index = operation.get("output_index", 0)
                    old_source, old_output_index = _connection_at(target, input_index)
                    rollback.connections.append((target, input_index, old_source, old_output_index))
                    target.setInput(input_index, source, output_index)
                    changes.append(
                        {
                            "op": op,
                            "from": source.path(),
                            "to": target.path(),
                            "input_index": input_index,
                            "output_index": output_index,
                            "previous_source": old_source.path() if old_source else None,
                            "previous_output_index": old_output_index,
                        }
                    )
                elif op == "set_parameter":
                    node = _resolve(operation["target"], refs)
                    parm = node.parm(operation["name"])
                    if parm is None:
                        raise ValueError(
                            f"node {node.path()} has no scalar parameter {operation['name']}"
                        )
                    old_keyframes = tuple(parm.keyframes())
                    if old_keyframes:
                        raise ValueError(
                            f"parameter {node.path()}/{operation['name']} has keyframes or an "
                            "expression; batch literal assignment would destroy authored state"
                        )
                    old_value = parm.eval()
                    rollback.parameters.append((parm, old_value, old_keyframes))
                    parm.set(operation["value"])
                    changes.append(
                        {
                            "op": op,
                            "path": node.path(),
                            "name": operation["name"],
                            "before": _json_value(old_value),
                            "after": operation["value"],
                        }
                    )
                elif op == "set_flags":
                    node = _resolve(operation["target"], refs)
                    before_flags = {
                        key: bool(getattr(node, getter)())
                        for key, getter in {
                            "display": "isDisplayFlagSet",
                            "render": "isRenderFlagSet",
                            "bypass": "isBypassed",
                        }.items()
                        if key in operation and hasattr(node, getter)
                    }
                    _set_flag(node, operation, rollback)
                    changes.append(
                        {
                            "op": op,
                            "path": node.path(),
                            "before": before_flags,
                            "after": {key: operation[key] for key in before_flags},
                        }
                    )
                elif op == "set_comment":
                    node = _resolve(operation["target"], refs)
                    old_comment = node.comment()
                    rollback.comments.append((node, old_comment))
                    node.setComment(operation["comment"])
                    changes.append(
                        {
                            "op": op,
                            "path": node.path(),
                            "before": old_comment,
                            "after": operation["comment"],
                        }
                    )

        after = snapshot_networks(parents, tracked_parameters)
        graph_diff = diff_snapshots(before, after)
        record.update(
            {
                "status": "success",
                "changes": changes,
                "graph_diff": graph_diff,
            }
        )
        append_replay_record(log_path, record)
        result.changed_nodes = [
            ChangedNode(hermes_id=item.get("hermes_id", ""), path=item["path"], change="created")
            for item in graph_diff["created"]
        ] + [ChangedNode(path=item["path"], change="modified") for item in graph_diff["modified"]]
        result.data = {
            "batch_id": batch_id,
            "operations_applied": len(normalized),
            "changes": changes,
            "graph_diff": graph_diff,
            "replay_log": log_path,
        }
        result.artifacts = [log_path]
        return result
    except Exception as exc:
        rollback_errors = rollback.restore()
        durable_restore_used = False
        if rollback_errors:
            try:
                restore_checkpoint(checkpoint, original_name)
                durable_restore_used = True
            except Exception as restore_exc:
                rollback_errors.append(f"checkpoint restore: {restore_exc}")
        rollback_succeeded = not rollback_errors or durable_restore_used
        result.status = Status.ERROR if rollback_succeeded else Status.PARTIAL
        result.errors.append(f"{type(exc).__name__}: {exc}")
        result.errors.extend(rollback_errors)
        result.data = {
            "batch_id": batch_id,
            "operations_applied_before_error": len(changes),
            "rolled_back": rollback_succeeded,
            "durable_restore_used": durable_restore_used,
            "changes_before_rollback": changes,
            "replay_log": log_path,
        }
        record.update(
            {
                "status": "rolled_back" if rollback_succeeded else "rollback_failed",
                "error": f"{type(exc).__name__}: {exc}",
                "rollback_errors": rollback_errors,
                "durable_restore_used": durable_restore_used,
                "changes_before_rollback": changes,
            }
        )
        try:
            append_replay_record(log_path, record)
            result.artifacts = [log_path]
        except Exception as log_exc:
            result.errors.append(f"replay log failure: {log_exc}")
            result.status = Status.PARTIAL
        return result


__all__ = [
    "BATCH_SCHEMA_VERSION",
    "MAX_BATCH_OPERATIONS",
    "append_replay_record",
    "apply_batch",
    "validate_batch",
    "validate_batch_options",
]
