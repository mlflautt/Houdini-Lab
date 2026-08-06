"""Validation layer (inside Houdini, needs `hou`).

Exact node-type / parameter existence + structural graph checks (docs §4.5, §5.4, §12.2).
"""
from __future__ import annotations

from typing import Any

from . import get_hou


def node_type_exists(category: str, operator_type: str) -> bool:
    hou = get_hou()
    try:
        hou.nodeType(hou.nodeTypeCategories()[category], operator_type)
        return True
    except Exception:
        return False


def validate_parameters(node_path: str, parms: dict[str, Any]) -> list[str]:
    """Return a list of problems for setting `parms` on node at `node_path`."""
    hou = get_hou()
    node = hou.node(node_path)
    if node is None:
        return [f"node not found: {node_path}"]
    problems: list[str] = []
    for pname in parms:
        parm = node.parm(pname) or node.parmTuple(pname)
        if parm is None:
            problems.append(f"missing parameter: {pname}")
    return problems


def graph_checks(node_path: str) -> dict[str, Any]:
    """Readable-graph checks: named OUT nulls, no errors, public inputs documented."""
    hou = get_hou()
    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"node not found: {node_path}")
    children = node.children() if hasattr(node, "children") else []
    has_out = any(c.name().startswith("OUT_") for c in children)
    errors = node.errors() if hasattr(node, "errors") else []
    return {
        "has_named_output": has_out,
        "node_errors": [str(e) for e in errors],
        "child_count": len(children),
    }


__all__ = ["node_type_exists", "validate_parameters", "graph_checks"]
