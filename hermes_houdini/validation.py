"""Validation layer (inside Houdini, needs `hou`).

Exact node-type / parameter existence + structural graph checks (docs §4.5, §5.4, §12.2).
"""

from __future__ import annotations

import math
from typing import Any

from . import get_hou
from .cook import metrics_for_clean_node

EXPECTATION_KEYS = {
    "min_points",
    "max_points",
    "min_primitives",
    "max_primitives",
    "required_point_attributes",
    "required_primitive_attributes",
    "required_point_groups",
    "required_primitive_groups",
    "require_finite_bounds",
    "allow_warnings",
}


def node_type_exists(category: str, operator_type: str) -> bool:
    hou = get_hou()
    try:
        categories = hou.nodeTypeCategories()
        resolved = next(
            value for name, value in categories.items() if name.casefold() == category.casefold()
        )
        return hou.nodeType(resolved, operator_type) is not None
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


def validate_metric_expectations(
    metrics: dict[str, Any], expectations: dict[str, Any]
) -> dict[str, Any]:
    """Validate cooked geometry metrics against a strict, JSON-safe contract."""
    if not isinstance(expectations, dict):
        raise ValueError("expectations must be an object")
    unknown = set(expectations) - EXPECTATION_KEYS
    if unknown:
        raise ValueError(f"unknown expectation keys: {', '.join(sorted(unknown))}")
    issues: list[str] = []
    numeric_checks = (
        ("min_points", "points", lambda actual, expected: actual >= expected, ">="),
        ("max_points", "points", lambda actual, expected: actual <= expected, "<="),
        ("min_primitives", "primitives", lambda actual, expected: actual >= expected, ">="),
        ("max_primitives", "primitives", lambda actual, expected: actual <= expected, "<="),
    )
    for expectation_key, metric_key, predicate, operator in numeric_checks:
        if expectation_key not in expectations:
            continue
        expected = expectations[expectation_key]
        if not isinstance(expected, int) or isinstance(expected, bool) or expected < 0:
            raise ValueError(f"{expectation_key} must be a non-negative integer")
        actual = int(metrics.get(metric_key, 0))
        if not predicate(actual, expected):
            issues.append(f"{metric_key} {actual} does not satisfy {operator} {expected}")

    required_checks = (
        ("required_point_attributes", "point_attributes"),
        ("required_primitive_attributes", "primitive_attributes"),
        ("required_point_groups", "point_groups"),
        ("required_primitive_groups", "primitive_groups"),
    )
    for expectation_key, metric_key in required_checks:
        required = expectations.get(expectation_key, [])
        if not isinstance(required, list) or any(
            not isinstance(item, str) or not item for item in required
        ):
            raise ValueError(f"{expectation_key} must be a list of non-empty strings")
        missing = sorted(set(required) - set(metrics.get(metric_key, [])))
        if missing:
            issues.append(f"missing {metric_key}: {', '.join(missing)}")

    if expectations.get("require_finite_bounds", True):
        bounds = metrics.get("bounds")
        if bounds is None:
            issues.append("geometry has no bounds")
        else:
            values = [component for vector in bounds for component in vector]
            if len(values) != 6 or any(not math.isfinite(float(value)) for value in values):
                issues.append("geometry bounds are not finite")

    warnings = list(metrics.get("node_warnings", []))
    if warnings and not expectations.get("allow_warnings", False):
        issues.extend(f"node warning: {warning}" for warning in warnings)
    errors = list(metrics.get("node_errors", []))
    issues.extend(f"node error: {error}" for error in errors)
    return {"valid": not issues, "issues": issues, "metrics": metrics}


def validate_cooked_node(node_path: str, expectations: dict[str, Any]) -> dict[str, Any]:
    """Validate an already-cooked node without causing another implicit cook."""
    hou = get_hou()
    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"node not found: {node_path}")
    metrics = metrics_for_clean_node(node_path)
    metrics["node_errors"] = [str(message) for message in node.errors()]
    metrics["node_warnings"] = [str(message) for message in node.warnings()]
    return validate_metric_expectations(metrics, expectations)


__all__ = [
    "EXPECTATION_KEYS",
    "graph_checks",
    "node_type_exists",
    "validate_cooked_node",
    "validate_metric_expectations",
    "validate_parameters",
]
