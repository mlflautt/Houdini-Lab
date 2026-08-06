"""model.fractal_relic — radial fractal relic generator skill.

Composes native SOP nodes + curated VEX into a readable, seeded, parameterized form.
The skill returns a sequence of bounded tool calls; the dispatcher executes them inside
Houdini. No opaque generated Python; every step is inspectable.
"""
from __future__ import annotations

from typing import Any

from .._lib import attribute_contract, build_envelope


def plan(parent_node_id: str, seed: int = 42, iterations: int = 4,
         detail_level: str = "preview") -> list[dict[str, Any]]:
    """Return ordered tool-call dicts to build the relic form graph."""
    calls: list[dict[str, Any]] = []
    # 1) base sphere
    calls.append(build_envelope("node.create", {
        "parent_path": parent_node_id,
        "operator_type": "sphere",
        "name": "SRC_BASE",
        "role": "relic_base",
        "parameters": {"type": 2, "radx": 1.0, "rady": 1.0, "radz": 1.0},
    }).as_dict())
    # 2) scatter points (curated recipe via node.create)
    calls.append(build_envelope("node.create", {
        "parent_path": parent_node_id,
        "operator_type": "scatter",
        "name": "SCATTER_PTS",
        "role": "relic_seeds",
        "parameters": {"force_total": 400 * iterations, "seed": seed, "relax": 0.4},
    }).as_dict())
    # 3) copy spheres to points (packed instances)
    calls.append(build_envelope("node.create", {
        "parent_path": parent_node_id,
        "operator_type": "copy",  # copy to points uses 'copy' node
        "name": "COPY_INSTANCES",
        "role": "relic_detail",
        "parameters": {"pack": 1},
    }).as_dict())
    # 4) named output null
    calls.append(build_envelope("node.create", {
        "parent_path": parent_node_id,
        "operator_type": "null",
        "name": "OUT_GEO",
        "role": "output",
        "comment": "Fractal relic output",
    }).as_dict())
    return calls


def attribute_contract_doc() -> dict[str, Any]:
    return attribute_contract()


__all__ = ["plan", "attribute_contract_doc"]
