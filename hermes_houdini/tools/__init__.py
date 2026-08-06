"""Tool implementations (inside Houdini when HOM is available).

Each function is a bounded operation registered with @tool. HOM is accessed lazily via
get_hou(); functions raise clearly when called without Houdini. Tools cover: system/license,
HIP, read-only graph, geometry, cook, foundational SOP edit, VEX template, HDA.
"""
from __future__ import annotations

from typing import Any

from .. import get_hou
from ..cook import check_budget, cook_node
from ..dispatcher import REGISTRY  # noqa: F401  (ensures registration target exists)
from ..ids import make_id
from ..inspect import describe_hip, describe_network, describe_node
from ..registry import tool
from ..transactions import save_checkpoint
from ..validation import node_type_exists


# ---------------- system / license ----------------
@tool("system.capabilities", risk="read_only", doc="Report Houdini build, Python, license, renderer.")
def system_capabilities() -> dict[str, Any]:
    hou = get_hou()
    import sys

    return {
        "houdini_version": hou.applicationVersionString(),
        "python_version": sys.version.split()[0],
        "license": hou.licenseCategory().name() if hasattr(hou, "licenseCategory") else "unknown",
    }


@tool("hip.describe", risk="read_only", doc="Summarize current HIP file.")
def hip_describe() -> dict[str, Any]:
    return describe_hip()


@tool("hip.create_checkpoint", risk="low",
      doc="Save an incremented .hipnc checkpoint before risky work.")
def hip_create_checkpoint(output_dir: str, stem: str = "hermes") -> dict[str, Any]:
    path = save_checkpoint(output_dir, stem)
    return {"checkpoint": path}


# ---------------- read-only graph ----------------
@tool("network.describe", risk="read_only", doc="List children of a network context.")
def network_describe(path: str = "/obj") -> dict[str, Any]:
    return describe_network(path)


@tool("node.describe", risk="read_only", doc="Describe a node's type/flags/errors/userdata.")
def node_describe(path: str) -> dict[str, Any]:
    return describe_node(path)


@tool("node.find_by_hermes_id", risk="read_only", doc="Resolve a stable Hermes id to a path.")
def node_find_by_hermes_id(hermes_id: str) -> dict[str, Any]:
    from ..inspect import find_by_hermes_id

    path = find_by_hermes_id(hermes_id)
    return {"path": path}


# ---------------- geometry ----------------
@tool("geometry.metrics", risk="read_only", doc="Point/primitive counts + bounds for a node.")
def geometry_metrics(node_path: str) -> dict[str, Any]:
    hou = get_hou()
    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"node not found: {node_path}")
    geo = node.geometry()
    bbox = geo.boundingBox() if geo else None
    return {
        "path": node_path,
        "points": len(geo.points()) if geo else 0,
        "primitives": len(geo.prims()) if geo else 0,
        "bounds": [list(bbox.minvec()), list(bbox.maxvec())] if bbox else None,
    }


# ---------------- foundational graph edit ----------------
@tool("node.create", risk="medium",
      doc="Create a node with stable id + comment; supports exact operator type.")
def node_create(parent_path: str, operator_type: str, name: str = "",
                category: str = "Sop", role: str = "",
                parameters: dict[str, Any] | None = None,
                comment: str = "") -> dict[str, Any]:
    hou = get_hou()
    parent = hou.node(parent_path)
    if parent is None:
        raise ValueError(f"parent not found: {parent_path}")
    if not node_type_exists(category, operator_type):
        raise ValueError(f"operator type {operator_type} not in category {category}")
    node = parent.createNode(operator_type, node_name=name or None,
                             exact_type_name=True)
    hermes_id = make_id(category, f"{parent_path}/{name or operator_type}")
    node.setUserData("hermes_id", hermes_id)
    node.setUserData("hermes_role", role)
    if comment:
        node.setComment(comment)
    if parameters:
        for k, v in parameters.items():
            parm = node.parm(k)
            if parm is not None:
                parm.set(v)
    return {
        "hermes_id": hermes_id,
        "path": node.path(),
        "type": node.type().name(),
        "category": category,
    }


@tool("node.connect", risk="medium", doc="Connect output of one node to an input of another.")
def node_connect(from_path: str, to_path: str, input_index: int = 0) -> dict[str, Any]:
    hou = get_hou()
    src = hou.node(from_path)
    dst = hou.node(to_path)
    if src is None or dst is None:
        raise ValueError("node not found")
    dst.setInput(input_index, src)
    return {"connected": [from_path, input_index, to_path]}


@tool("node.set_parameter", risk="low", doc="Set a single parameter (preserves expressions if present).")
def node_set_parameter(path: str, name: str, value: Any) -> dict[str, Any]:
    hou = get_hou()
    node = hou.node(path)
    if node is None:
        raise ValueError(f"node not found: {path}")
    parm = node.parm(name)
    if parm is None:
        raise ValueError(f"missing parameter {name}")
    if parm.expression() and not isinstance(value, str):
        # do not clobber an expression with a literal
        raise ValueError(f"parameter {name} has an expression; use set_expression")
    parm.set(value)
    return {"path": path, "parm": name, "value": value}


# ---------------- cook ----------------
@tool("cook.node", risk="low", doc="Cook a single node within declared budget.")
def cook_node_tool(node_path: str, max_points: int = 1_000_000) -> dict[str, Any]:
    from ..schemas.command import Policy

    est = cook_node(node_path)
    ok, msg = check_budget(est.get("points", 0), Policy(max_points=max_points))
    if not ok:
        return {"error": msg, **est}
    return est


# ---------------- VEX template ----------------
@tool("vex.validate_snippet", risk="read_only", doc="Sanity-check a VEX snippet text.")
def vex_validate_snippet(code: str) -> dict[str, Any]:
    # Lightweight structural check; real compile needs Houdini VEX context.
    issues = []
    if "@" in code and "float" not in code and "int" not in code and "vector" not in code:
        issues.append("uses @ attributes but no type declaration found")
    if code.count("{") != code.count("}"):
        issues.append("unbalanced braces")
    return {"valid": not issues, "issues": issues}


# ---------------- HDA ----------------
@tool("hda.create_from_subnet", risk="medium",
      doc="Wrap a subnet into a namespaced, versioned HDA definition.")
def hda_create_from_subnet(subnet_path: str, namespace: str = "hermes",
                           name: str = "tool", version: str = "1.0") -> dict[str, Any]:
    hou = get_hou()
    subnet = hou.node(subnet_path)
    if subnet is None:
        raise ValueError(f"subnet not found: {subnet_path}")
    type_name = f"{namespace}::{name}::{version}"
    subnet.createDigitalAsset(
        name=type_name, hda_file_name=None, save_as_embedded=True
    )
    return {
        "type_name": type_name,
        "namespace": namespace,
        "version": version,
        "noncommercial": True,
    }


__all__ = ["REGISTRY"]
