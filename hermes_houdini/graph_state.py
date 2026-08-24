"""Compact graph snapshots and deterministic diffs.

Snapshot collection needs Houdini, while :func:`diff_snapshots` is deliberately
pure Python so it can be unit-tested and consumed by an external orchestrator.
"""

from __future__ import annotations

from typing import Any

from . import get_hou


def _flag(node: Any, method: str) -> bool | None:
    getter = getattr(node, method, None)
    if getter is None:
        return None
    try:
        return bool(getter())
    except Exception:
        return None


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    try:
        return [_json_value(item) for item in value]
    except TypeError:
        return str(value)


def snapshot_networks(
    parent_paths: list[str],
    tracked_parameters: dict[str, set[str]] | None = None,
) -> dict[str, Any]:
    """Snapshot direct children of the named networks without cooking geometry."""
    hou = get_hou()
    networks: dict[str, Any] = {}
    for parent_path in sorted(set(parent_paths)):
        parent = hou.node(parent_path)
        if parent is None:
            raise ValueError(f"network not found: {parent_path}")
        nodes: dict[str, Any] = {}
        for node in sorted(parent.children(), key=lambda item: item.path()):
            inputs = []
            for connection in node.inputConnections():
                inputs.append(
                    {
                        "input_index": connection.inputIndex(),
                        "source_path": connection.inputNode().path(),
                        "output_index": connection.outputIndex(),
                    }
                )
            parameters = {}
            for name in sorted((tracked_parameters or {}).get(node.path(), set())):
                parm = node.parm(name)
                parameters[name] = _json_value(parm.eval()) if parm is not None else None
            nodes[node.path()] = {
                "type": node.type().name(),
                "category": node.type().category().name(),
                "hermes_id": node.userData("hermes_id") or "",
                "hermes_role": node.userData("hermes_role") or "",
                "hermes_batch_id": node.userData("hermes_batch_id") or "",
                "comment": node.comment(),
                "flags": {
                    "display": _flag(node, "isDisplayFlagSet"),
                    "render": _flag(node, "isRenderFlagSet"),
                    "bypass": _flag(node, "isBypassed"),
                },
                "inputs": sorted(inputs, key=lambda item: item["input_index"]),
                "parameters": parameters,
            }
        networks[parent_path] = {"nodes": nodes}
    return {"networks": networks}


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Return created/deleted/modified node records for two snapshots."""
    before_nodes = {
        path: node
        for network in before.get("networks", {}).values()
        for path, node in network.get("nodes", {}).items()
    }
    after_nodes = {
        path: node
        for network in after.get("networks", {}).values()
        for path, node in network.get("nodes", {}).items()
    }
    before_paths = set(before_nodes)
    after_paths = set(after_nodes)
    created = [{"path": path, **after_nodes[path]} for path in sorted(after_paths - before_paths)]
    deleted = [{"path": path, **before_nodes[path]} for path in sorted(before_paths - after_paths)]
    modified = []
    for path in sorted(before_paths & after_paths):
        old = before_nodes[path]
        new = after_nodes[path]
        if old == new:
            continue
        fields = {
            key: {"before": old.get(key), "after": new.get(key)}
            for key in sorted(set(old) | set(new))
            if old.get(key) != new.get(key)
        }
        modified.append({"path": path, "fields": fields})
    return {"created": created, "deleted": deleted, "modified": modified}


__all__ = ["diff_snapshots", "snapshot_networks", "_json_value"]
