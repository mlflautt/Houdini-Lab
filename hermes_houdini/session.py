"""Read-only Houdini session bootstrap and compatibility inventory."""

from __future__ import annotations

import os
import sys
from collections import deque
from typing import Any

from . import __version__, get_hou
from .execution import current_envelope, current_runtime_state
from .schemas.command import PROTOCOL_VERSION
from .schemas.control_plane import CompatibilityIdentity


def _license_name(hou: Any) -> str:
    category = hou.licenseCategory()
    name = getattr(category, "name", None)
    return str(name() if callable(name) else category)


def compatibility_identity(hou: Any) -> CompatibilityIdentity:
    dependencies = []
    for name in ("MOPS", "SIDEFXLABS"):
        if hou.getenv(name):
            dependencies.append(name.lower())
    return CompatibilityIdentity(
        houdini_build=str(hou.applicationVersionString()),
        python_version=sys.version.split()[0],
        license_mode=_license_name(hou),
        package_version=__version__,
        protocol_version=PROTOCOL_VERSION,
        optional_dependencies=tuple(dependencies),
    )


def _managed_nodes(hou: Any, *, max_nodes_scanned: int, max_managed_nodes: int) -> dict[str, Any]:
    root = hou.node("/")
    if root is None:
        return {"nodes": [], "scanned": 0, "truncated": False}
    queue = deque(root.children())
    scanned = 0
    managed: list[dict[str, str]] = []
    while queue and scanned < max_nodes_scanned and len(managed) < max_managed_nodes:
        node = queue.popleft()
        scanned += 1
        hermes_id = node.userData("hermes_id")
        if hermes_id:
            managed.append(
                {
                    "hermes_id": str(hermes_id),
                    "path": str(node.path()),
                    "role": str(node.userData("hermes_role") or ""),
                    "created_by": str(node.userData("hermes_created_by") or ""),
                    "operator_type": str(node.type().name()),
                    "category": str(node.type().category().name()),
                }
            )
        try:
            queue.extend(node.children())
        except Exception:
            continue
    return {"nodes": managed, "scanned": scanned, "truncated": bool(queue)}


def _timeline_range(hou: Any) -> tuple[list[float], str]:
    try:
        timeline = hou.playbar.timelineRange()
        return [float(timeline[0]), float(timeline[1])], "playbar.timelineRange"
    except hou.NotAvailable:
        # Hython has no playbar UI. FSTART/FEND are the equivalent global animation range.
        return [
            float(hou.hscriptExpression("$FSTART")),
            float(hou.hscriptExpression("$FEND")),
        ], "hscript.FSTART_FEND"


def describe_session(*, max_nodes_scanned: int = 5000, max_managed_nodes: int = 256) -> dict[str, Any]:
    """Describe session state without changing frame, flags, nodes, or cook state."""
    if not isinstance(max_nodes_scanned, int) or not 1 <= max_nodes_scanned <= 20_000:
        raise ValueError("max_nodes_scanned must be between 1 and 20000")
    if not isinstance(max_managed_nodes, int) or not 1 <= max_managed_nodes <= 2_000:
        raise ValueError("max_managed_nodes must be between 1 and 2000")
    hou = get_hou()
    runtime = current_runtime_state()
    envelope = current_envelope()
    timeline, timeline_source = _timeline_range(hou)
    return {
        "schema": "hermes.houdini.session_snapshot",
        "schema_version": "1.0",
        "compatibility": compatibility_identity(hou).as_dict(),
        "session_id": envelope.session_id if envelope else "",
        "project_id": envelope.project_id if envelope else "",
        "hip_path": str(hou.hipFile.path()),
        "job": str(hou.getenv("JOB") or ""),
        "frame": float(hou.frame()),
        "timeline_range": timeline,
        "timeline_range_source": timeline_source,
        "bridge_mode": str(
            runtime.get(
                "bridge_mode",
                os.environ.get("HERMES_HOUDINI_BRIDGE_MODE", "local-dispatcher"),
            )
        ),
        "packages": {
            "houdini_path_entry_count": len(hou.houdiniPath()),
            "mops_loaded": bool(hou.getenv("MOPS")),
            "sidefx_labs_loaded": bool(hou.getenv("SIDEFXLABS")),
            "package_skiplist_active": bool(hou.getenv("HOUDINI_PACKAGE_SKIPLIST")),
        },
        "policy": dict(runtime.get("policy", {})),
        "pending_approvals": list(runtime.get("pending_approvals", [])),
        "pending_cooks": list(runtime.get("pending_cooks", [])),
        "managed_nodes": _managed_nodes(
            hou,
            max_nodes_scanned=max_nodes_scanned,
            max_managed_nodes=max_managed_nodes,
        ),
        "cook_scope": "none",
    }


__all__ = ["compatibility_identity", "describe_session"]
