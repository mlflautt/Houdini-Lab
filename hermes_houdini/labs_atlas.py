"""Capability-gated SideFX Labs enhancements for the native World Seed Atlas."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from . import get_hou
from .cook import geometry_metrics
from .execution import current_envelope
from .world_seed import validate_world_seed_spec

LABS_ATLAS_NODE_TYPES = (
    "labs::terrain_analysis::1.0",
    "labs::measure_curvature::3.1",
    "labs::instance_attributes::1.0",
)


def detect_labs_atlas_capability(node_type_names: Iterable[str]) -> dict[str, Any]:
    """Return an exact, serializable capability decision for the three certified nodes."""
    available = {str(name) for name in node_type_names}
    missing = [name for name in LABS_ATLAS_NODE_TYPES if name not in available]
    return {
        "available": not missing,
        "required_node_types": list(LABS_ATLAS_NODE_TYPES),
        "missing_node_types": missing,
        "scope": "three_certified_sidefx_labs_sop_types_only",
    }


def validate_labs_atlas_spec(
    *, base_seed: int, terrain_samples: int, world_size: float, labs_available: bool
) -> dict[str, Any]:
    """Extend the native three-world spec without ranking native and Labs branches."""
    if not isinstance(labs_available, bool):
        raise ValueError("labs_available must be boolean")
    native = validate_world_seed_spec(
        base_seed=base_seed, terrain_samples=terrain_samples, world_size=world_size
    )
    candidates = []
    for candidate in native["candidates"]:
        candidates.append(
            {
                "id": candidate["id"],
                "seed": candidate["seed"],
                "branches": [
                    {
                        "id": "native",
                        "available": True,
                        "human_rating": {"score": None, "notes": ""},
                        "automatic_rank": None,
                    },
                    {
                        "id": "labs",
                        "available": labs_available,
                        "human_rating": {"score": None, "notes": ""},
                        "automatic_rank": None,
                    },
                ],
            }
        )
    return {
        "schema": "hermes.houdini.labs_world_seed_atlas_spec",
        "schema_version": "1.0",
        "native_spec": native,
        "plugin": {
            "id": "sidefx-labs-22.0.368",
            "available": labs_available,
            "required_node_types": list(LABS_ATLAS_NODE_TYPES),
            "fallback": "native_graph_plus_OPTIONAL_LABS_UNAVAILABLE_contract",
        },
        "candidates": candidates,
        "selection": {
            "method": "human",
            "winner": None,
            "automatic_ranking": False,
        },
    }


def _safe_node_path(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("/") or ".." in value.split("/"):
        raise ValueError(f"{label} must be an absolute Houdini node path")
    return value


def _messages(node: Any) -> tuple[list[str], list[str]]:
    return list(node.errors()), list(node.warnings())


def cook_validate_labs_atlas(
    *,
    candidate_contracts: list[dict[str, str]],
    base_seed: int,
    terrain_samples: int,
    world_size: float,
    labs_available: bool,
    output_path: str,
    max_points: int = 300_000,
    max_primitives: int = 300_000,
    max_seconds: float = 180.0,
) -> dict[str, Any]:
    """Cook exact native/Labs contracts and retain an explicit no-plugin fallback."""
    hou = get_hou()
    spec = validate_labs_atlas_spec(
        base_seed=base_seed,
        terrain_samples=terrain_samples,
        world_size=world_size,
        labs_available=labs_available,
    )
    if not isinstance(candidate_contracts, list) or len(candidate_contracts) != 3:
        raise ValueError("candidate_contracts must contain exactly three worlds")
    if not isinstance(max_seconds, (int, float)) or max_seconds <= 0:
        raise ValueError("max_seconds must be positive")
    output = Path(output_path).expanduser()
    if not output.is_absolute() or output.suffix.lower() != ".json":
        raise ValueError("output_path must be an absolute JSON path")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite validation artifact: {output}")

    started = time.monotonic()
    results: list[dict[str, Any]] = []
    total_points = 0
    total_primitives = 0
    capability = detect_labs_atlas_capability(hou.sopNodeTypeCategory().nodeTypes())
    if labs_available and not capability["available"]:
        raise ValueError(f"Labs enhancement requested but unavailable: {capability['missing_node_types']}")

    for expected, contract in zip(spec["candidates"], candidate_contracts, strict=True):
        if not isinstance(contract, dict) or contract.get("id") != expected["id"]:
            raise ValueError("candidate contracts must preserve the registered world order")
        network = hou.node(_safe_node_path(contract.get("network_path", ""), "network_path"))
        if network is None or network.type().category().name() != "Object":
            raise ValueError(f"world network not found: {contract.get('network_path')}")
        required = {
            "native_world_path",
            "selector_path",
            "selected_path",
            "comparison_path",
        }
        required.add("labs_world_path" if labs_available else "unavailable_path")
        if labs_available:
            required.update(
                {"terrain_analysis_path", "curvature_path", "instance_attributes_path"}
            )
        missing_keys = sorted(key for key in required if key not in contract)
        if missing_keys:
            raise ValueError(f"world {expected['id']} contract is missing {missing_keys}")
        nodes = {
            key.removesuffix("_path"): hou.node(_safe_node_path(contract[key], key))
            for key in required
        }
        if any(node is None or node.parent() != network for node in nodes.values()):
            raise ValueError(f"world {expected['id']} has missing or foreign contract nodes")
        if nodes["selector"].type().name().split("::")[0] != "switch":
            raise ValueError(f"world {expected['id']} selector is not a Switch SOP")
        if int(nodes["selector"].parm("input").eval()) != 0:
            raise ValueError("Labs atlas defaults must retain the native branch")
        if labs_available:
            expected_types = {
                "terrain_analysis": LABS_ATLAS_NODE_TYPES[0],
                "curvature": LABS_ATLAS_NODE_TYPES[1],
                "instance_attributes": LABS_ATLAS_NODE_TYPES[2],
            }
            for key, node_type in expected_types.items():
                if nodes[key].type().name() != node_type:
                    raise ValueError(f"world {expected['id']} has wrong {key} node type")
            attribute_contracts = {
                "terrain_analysis": {"Cd", "slope"},
                "curvature": {"Cd", "concavity", "convexity"},
                "instance_attributes": {"orient", "pscale", "scale"},
            }
            for key, required_attributes in attribute_contracts.items():
                nodes[key].cook(force=True)
                metrics = geometry_metrics(nodes[key])
                absent = required_attributes.difference(metrics["point_attributes"])
                if absent:
                    raise ValueError(
                        f"world {expected['id']} {key} missing attributes: {sorted(absent)}"
                    )
        elif nodes["unavailable"].userData("hermes_role") != "labs_atlas_unavailable":
            raise ValueError("plugin-disabled graph lacks OPTIONAL_LABS_UNAVAILABLE contract")

        branch_results = {}
        for key in ("native_world", "selected", "comparison"):
            node = nodes[key]
            node.cook(force=True)
            errors, warnings = _messages(node)
            if errors or warnings:
                raise ValueError(f"world {expected['id']} {key} has Houdini messages")
            metrics = geometry_metrics(node)
            if metrics["points"] <= 0 or metrics["primitives"] <= 0:
                raise ValueError(f"world {expected['id']} {key} is empty")
            branch_results[key] = metrics
        if labs_available:
            nodes["labs_world"].cook(force=True)
            errors, warnings = _messages(nodes["labs_world"])
            if errors or warnings:
                raise ValueError(f"world {expected['id']} Labs branch has Houdini messages")
            labs_metrics = geometry_metrics(nodes["labs_world"])
            if labs_metrics["points"] <= 0 or labs_metrics["primitives"] <= 0:
                raise ValueError(f"world {expected['id']} Labs branch is empty")
            branch_results["labs_world"] = labs_metrics
        total_points += int(branch_results["comparison"]["points"])
        total_primitives += int(branch_results["comparison"]["primitives"])
        if total_points > max_points or total_primitives > max_primitives:
            raise ValueError("Labs Atlas exceeds geometry policy budget")
        results.append(
            {
                "id": expected["id"],
                "seed": expected["seed"],
                "network_path": network.path(),
                "metrics": branch_results,
                "branches": expected["branches"],
                "automatic_rank": None,
            }
        )
        if time.monotonic() - started > max_seconds:
            raise TimeoutError("Labs Atlas validation exceeded max_seconds")

    document = {
        "schema": "hermes.houdini.labs_world_seed_atlas_validation",
        "schema_version": "1.0",
        "status": "success",
        "houdini": {
            "build": hou.applicationVersionString(),
            "license": hou.licenseCategory().name(),
        },
        "request": current_envelope().as_dict() if current_envelope() else None,
        "capability": capability,
        "spec": spec,
        "candidates": results,
        "total_points": total_points,
        "total_primitives": total_primitives,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "selection": spec["selection"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "artifact": str(output),
        "capability": capability,
        "candidates": results,
        "total_points": total_points,
        "total_primitives": total_primitives,
        "selection": spec["selection"],
    }


__all__ = [
    "LABS_ATLAS_NODE_TYPES",
    "cook_validate_labs_atlas",
    "detect_labs_atlas_capability",
    "validate_labs_atlas_spec",
]
