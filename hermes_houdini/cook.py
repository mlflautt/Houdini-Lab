"""Cook + cache controller (inside Houdini, needs `hou`).

Enforces explicit cook scope + resource budget (docs §4.8, §11.5). Never force-cooks a
full range after every edit; cook only the intended output/frame.
"""
from __future__ import annotations

from typing import Any

from . import get_hou
from .schemas.command import Policy


def estimate(node_path: str) -> dict[str, Any]:
    """Cheap estimate of cook cost for a node's display chain."""
    hou = get_hou()
    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"node not found: {node_path}")
    geo = node.geometry() if hasattr(node, "geometry") else None
    pts = len(geo.points()) if geo is not None else 0
    prims = len(geo.prims()) if geo is not None else 0
    return {"path": node_path, "points": pts, "primitives": prims}


def cook_node(node_path: str, policy: Policy | None = None) -> dict[str, Any]:
    """Cook a single node and report scope/metrics. No range, no force-spam."""
    hou = get_hou()
    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"node not found: {node_path}")
    import time

    t0 = time.time()
    node.cook(force=True)
    dt = time.time() - t0
    geo = node.geometry() if hasattr(node, "geometry") else None
    return {
        "scope": "single_node",
        "seconds": round(dt, 4),
        "points": len(geo.points()) if geo else 0,
        "primitives": len(geo.prims()) if geo else 0,
    }


def check_budget(estimated_points: int, policy: Policy | None = None) -> tuple[bool, str]:
    pol = policy or Policy()
    if estimated_points > pol.max_points:
        return False, f"points {estimated_points} > budget {pol.max_points}"
    return True, ""


__all__ = ["estimate", "cook_node", "check_budget"]
