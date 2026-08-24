"""Graph inspector (inside Houdini, needs `hou`).

Returns compact structured info rather than dumping the whole HIP. Safe to import
without Houdini; all HOM access is inside functions guarded by has_hou().
"""

from __future__ import annotations

from typing import Any

from . import get_hou


def describe_hip() -> dict[str, Any]:
    hou = get_hou()
    return {
        "name": hou.hipFile.name(),
        "path": hou.hipFile.path() or None,
        "is_loaded": hou.hipFile.isLoaded(),
        "version": hou.applicationVersionString(),
        "build": hou.applicationVersion(),
    }


def list_contexts() -> list[str]:
    hou = get_hou()
    return [c.name() for c in hou.node("/").children()]


def describe_node(path: str) -> dict[str, Any]:
    hou = get_hou()
    node = hou.node(path)
    if node is None:
        raise ValueError(f"node not found: {path}")
    return {
        "path": node.path(),
        "name": node.name(),
        "type": node.type().name(),
        "category": node.type().category().name(),
        "comment": node.comment(),
        "user_data": node.userDataDict() or {},
        "errors": node.errors() if hasattr(node, "errors") else [],
        "flags_display": node.isDisplayFlagSet() if hasattr(node, "isDisplayFlagSet") else None,
        "flags_render": node.isRenderFlagSet() if hasattr(node, "isRenderFlagSet") else None,
    }


def describe_network(path: str = "/obj") -> dict[str, Any]:
    hou = get_hou()
    parent = hou.node(path)
    if parent is None:
        raise ValueError(f"network not found: {path}")
    children = []
    for c in parent.children():
        children.append(
            {
                "path": c.path(),
                "name": c.name(),
                "type": c.type().name(),
                "category": c.type().category().name(),
                "hermes_id": c.userData("hermes_id") or "",
            }
        )
    return {"path": path, "child_count": len(children), "children": children}


def find_by_hermes_id(hermes_id: str) -> str | None:
    hou = get_hou()
    for node in hou.node("/").allSubChildren():
        if node.userData("hermes_id") == hermes_id:
            return node.path()
    return None


__all__ = [
    "describe_hip",
    "list_contexts",
    "describe_node",
    "describe_network",
    "find_by_hermes_id",
]
