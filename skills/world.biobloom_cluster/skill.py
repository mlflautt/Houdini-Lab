"""world.biobloom_cluster — clustered procedural alien botanical form skill.

Composes two curated recipes (scatter cluster + sweep petals) into a readable bloom.
Hermes calls recipe `render()` to get bounded tool calls, then executes them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from recipes.parser import load_recipe
from skills._lib import attribute_contract, build_envelope

_RECIPES = Path(__file__).resolve().parents[2] / "recipes"


def plan(
    parent_node_id: str,
    seed: int = 42,
    cluster_count: int = 24,
    growth_bias: float = 0.65,
    detail_level: str = "preview",
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    scatter = load_recipe(_RECIPES / "sop" / "scatter_cluster_points.yaml")
    calls += scatter.render(
        parent_node_id,
        surface_path=f"{parent_node_id.rstrip('/')}/IN_GEO",
        count=cluster_count,
        seed=seed,
    )
    calls.append(
        build_envelope(
            "node.create",
            {
                "parent_path": parent_node_id,
                "operator_type": "null",
                "name": "OUT_GEO",
                "role": "output",
                "comment": (f"Biobloom cluster (growth_bias={growth_bias}, detail={detail_level})"),
            },
        ).as_dict()
    )
    return calls


__all__ = ["plan", "attribute_contract"]
