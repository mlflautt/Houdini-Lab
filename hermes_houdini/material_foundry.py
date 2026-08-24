"""Native Copernicus PBR-channel and USD Material validation for Sprint 18.

Specification checks remain pure Python. HOM is used only by the bounded cook validator.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from . import get_hou
from .copernicus import _layer_metrics
from .execution import current_envelope

FOUNDRY_CANDIDATES = ("verdigris", "emberglaze", "moonlichen")
PBR_CHANNELS = ("base_color", "roughness", "height", "normal")
COLOR_SPACE_INTENT = {
    "base_color": "scene_linear_rec709",
    "roughness": "raw_data",
    "height": "raw_data",
    "normal": "raw_data_offset_0_1",
}
FOUNDRY_RESOLUTIONS = (64, 128, 256, 512, 1024)


def validate_foundry_spec(
    *,
    resolution: int,
    candidate_index: int,
    candidate_ids: list[str] | tuple[str, ...] = FOUNDRY_CANDIDATES,
) -> dict[str, Any]:
    """Validate a bounded, fixed-order three-material comparison specification."""
    if resolution not in FOUNDRY_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {list(FOUNDRY_RESOLUTIONS)}")
    if (
        not isinstance(candidate_index, int)
        or isinstance(candidate_index, bool)
        or not 0 <= candidate_index <= 2
    ):
        raise ValueError("candidate_index must be an integer between 0 and 2")
    if tuple(candidate_ids) != FOUNDRY_CANDIDATES:
        raise ValueError(f"candidate_ids must preserve exact order {list(FOUNDRY_CANDIDATES)}")
    return {
        "resolution": resolution,
        "candidate_index": candidate_index,
        "candidate_ids": list(FOUNDRY_CANDIDATES),
        "channels": list(PBR_CHANNELS),
        "color_space_intent": dict(COLOR_SPACE_INTENT),
        "automatic_ranking": False,
    }


def _path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("/") or value == "/":
        raise ValueError(f"{label} must be an absolute Houdini node path")
    return value


def _candidate_contracts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("candidate_contracts must contain exactly three candidates")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or item.get("id") != FOUNDRY_CANDIDATES[index]:
            raise ValueError("candidate_contracts must preserve the registered candidate order")
        channels = item.get("channels")
        if not isinstance(channels, dict) or set(channels) != set(PBR_CHANNELS):
            raise ValueError(
                f"candidate {item.get('id')} must declare exactly {list(PBR_CHANNELS)}"
            )
        normalized.append(
            {
                "id": item["id"],
                "channels": {
                    name: _path(channels[name], f"{item['id']}.{name}") for name in PBR_CHANNELS
                },
                "material": _path(item.get("material"), f"{item['id']}.material"),
            }
        )
    return normalized


def cook_validate_material_foundry(
    *,
    network_path: str,
    candidate_contracts: list[dict[str, Any]],
    resolution: int,
    candidate_index: int,
    output_path: str,
    minimum_dynamic_range: float = 0.015,
) -> dict[str, Any]:
    """Cook four channels per candidate and verify their native USD Material wiring."""
    hou = get_hou()
    spec = validate_foundry_spec(resolution=resolution, candidate_index=candidate_index)
    contracts = _candidate_contracts(candidate_contracts)
    network = hou.node(_path(network_path, "network_path"))
    if network is None or network.type().category().name() != "CopNet":
        raise ValueError(f"Copernicus network not found: {network_path}")
    output = Path(output_path).expanduser()
    if not output.is_absolute() or output.suffix.lower() != ".json":
        raise ValueError("output_path must be an absolute .json path")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {output}")
    if not isinstance(minimum_dynamic_range, (int, float)) or not math.isfinite(
        minimum_dynamic_range
    ):
        raise ValueError("minimum_dynamic_range must be finite")

    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    max_seconds = float(policy.max_seconds) if policy else 90.0
    max_memory = int(policy.max_memory_bytes) if policy else 1_073_741_824
    started = time.monotonic()
    all_hashes: dict[str, str] = {}
    candidate_results: list[dict[str, Any]] = []
    expected_components = {"base_color": 3, "roughness": 1, "height": 1, "normal": 3}
    expected_types = {"base_color": "null", "roughness": "null", "height": "null", "normal": "null"}
    material_inputs = {"base_color": 0, "roughness": 3, "height": 12, "normal": 13}

    for contract in contracts:
        channel_results: dict[str, Any] = {}
        nodes: dict[str, Any] = {}
        for channel in PBR_CHANNELS:
            node = hou.node(contract["channels"][channel])
            if (
                node is None
                or node.parent() != network
                or node.type().name() != expected_types[channel]
            ):
                raise ValueError(f"invalid managed channel contract: {contract['id']}.{channel}")
            expected_role = f"material_foundry_{contract['id']}_{channel}"
            if node.userData("hermes_role") != expected_role:
                raise ValueError(f"stale role for {contract['id']}.{channel}")
            node.cook(force=True)
            metrics = _layer_metrics(node, expected_resolution=(resolution, resolution))
            if metrics["components"] != expected_components[channel]:
                raise ValueError(f"{contract['id']}.{channel} has wrong component count")
            if metrics["nonfinite_values"]:
                raise ValueError(f"{contract['id']}.{channel} contains non-finite values")
            if metrics["dynamic_range"] < minimum_dynamic_range:
                raise ValueError(f"{contract['id']}.{channel} has insufficient dynamic range")
            if metrics["node_errors"] or metrics["node_warnings"]:
                raise ValueError(f"{contract['id']}.{channel} has Houdini messages")
            if channel in {"roughness", "height", "normal"} and (
                metrics["minimum"] < -1e-5 or metrics["maximum"] > 1.00001
            ):
                raise ValueError(f"{contract['id']}.{channel} leaves its raw 0..1 contract")
            metrics["color_space_intent"] = COLOR_SPACE_INTENT[channel]
            metrics["seconds"] = round(float(node.lastCookTime()), 6)
            channel_results[channel] = metrics
            nodes[channel] = node
            all_hashes[f"{contract['id']}:{channel}"] = metrics["buffer_sha256"]
            if time.monotonic() - started > max_seconds:
                raise TimeoutError("material-foundry validation exceeded policy.max_seconds")

        material = hou.node(contract["material"])
        if (
            material is None
            or material.parent() != network
            or material.type().name() != "usdmaterial"
        ):
            raise ValueError(f"invalid USD Material COP for {contract['id']}")
        if material.userData("hermes_role") != f"material_foundry_{contract['id']}_usd_material":
            raise ValueError(f"stale USD Material role for {contract['id']}")
        for channel, input_index in material_inputs.items():
            if material.input(input_index) != nodes[channel]:
                raise ValueError(f"USD Material {contract['id']} is not wired to {channel}")
        candidate_results.append(
            {
                "id": contract["id"],
                "channels": channel_results,
                "usd_material_cop": material.path(),
                "human_rating": {"score": None, "notes": "", "selected": False},
                "automatic_rank": None,
            }
        )

    # Every candidate must carry a distinct base-color identity; no auto-winner is inferred.
    base_hashes = [all_hashes[f"{candidate}:base_color"] for candidate in FOUNDRY_CANDIDATES]
    if len(set(base_hashes)) != 3:
        raise ValueError("material candidates do not have distinct base-color channels")
    total_memory = sum(
        channel["memory_bytes"]
        for candidate in candidate_results
        for channel in candidate["channels"].values()
    )
    if total_memory > max_memory:
        raise ValueError("observed material buffers exceed policy.max_memory_bytes")
    elapsed = time.monotonic() - started
    if elapsed > max_seconds:
        raise TimeoutError("material-foundry validation exceeded policy.max_seconds")

    document = {
        "schema": "hermes.houdini.material_foundry_validation",
        "schema_version": "1.0",
        "status": "success",
        "houdini": {
            "build": hou.applicationVersionString(),
            "license": hou.licenseCategory().name(),
        },
        "request": envelope.as_dict() if envelope else None,
        "network_path": network.path(),
        "spec": spec,
        "candidates": candidate_results,
        "elapsed_seconds": round(elapsed, 6),
        "total_buffer_memory_bytes": total_memory,
        "selection": {
            "method": "human",
            "preview_input": candidate_index,
            "winner": None,
            "automatic_ranking": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "artifact": str(output),
        "network_path": network.path(),
        "spec": spec,
        "candidates": candidate_results,
        "elapsed_seconds": document["elapsed_seconds"],
        "total_buffer_memory_bytes": total_memory,
        "selection": document["selection"],
    }


def validate_material_foundry_stage(
    *, stage_node_path: str, bindings: list[dict[str, str]], max_prims: int = 10000
) -> dict[str, Any]:
    """Compose one stage and verify all three material bindings plus MaterialX outputs."""
    hou = get_hou()
    from pxr import UsdShade

    if not isinstance(bindings, list) or len(bindings) != 3:
        raise ValueError("bindings must contain exactly three swatch/material pairs")
    if not isinstance(max_prims, int) or isinstance(max_prims, bool) or max_prims < 1:
        raise ValueError("max_prims must be a positive integer")
    node = hou.node(_path(stage_node_path, "stage_node_path"))
    if node is None or node.type().category().name() != "Lop":
        raise ValueError(f"LOP stage contract not found: {stage_node_path}")
    started = time.monotonic()
    stage = node.stage()
    prim_count = sum(1 for _ in stage.Traverse())
    if prim_count > max_prims:
        raise ValueError("stage prim count exceeds max_prims")
    results: list[dict[str, Any]] = []
    for item in bindings:
        if not isinstance(item, dict) or set(item) != {
            "candidate_id",
            "prim_path",
            "material_path",
        }:
            raise ValueError("each binding requires candidate_id, prim_path, and material_path")
        candidate_id = item["candidate_id"]
        if candidate_id not in FOUNDRY_CANDIDATES:
            raise ValueError(f"unregistered material candidate: {candidate_id}")
        prim_path = _path(item["prim_path"], f"{candidate_id}.prim_path")
        material_path = _path(item["material_path"], f"{candidate_id}.material_path")
        prim = stage.GetPrimAtPath(prim_path)
        material_prim = stage.GetPrimAtPath(material_path)
        if not prim.IsValid() or not material_prim.IsValid():
            raise ValueError(f"missing swatch or material prim for {candidate_id}")
        bound, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        if not bound or str(bound.GetPath()) != material_path:
            raise ValueError(f"incorrect material binding for {candidate_id}")
        material = UsdShade.Material(material_prim)
        outputs = material.GetOutputs()
        materialx_outputs = [
            str(output.GetFullName())
            for output in outputs
            if "mtlx" in str(output.GetFullName()).lower() and output.HasConnectedSource()
        ]
        if not materialx_outputs:
            raise ValueError(f"material {candidate_id} has no connected MaterialX output")
        results.append(
            {
                "candidate_id": candidate_id,
                "prim_path": prim_path,
                "material_path": material_path,
                "materialx_outputs": materialx_outputs,
            }
        )
    elapsed = time.monotonic() - started
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    if policy and elapsed > policy.max_seconds:
        raise TimeoutError("material-foundry stage validation exceeded policy.max_seconds")
    return {
        "stage_node_path": node.path(),
        "prim_count": prim_count,
        "bindings": results,
        "elapsed_seconds": round(elapsed, 6),
        "material_system": "MaterialX",
        "selection": {"method": "human", "winner": None, "automatic_ranking": False},
    }


__all__ = [
    "COLOR_SPACE_INTENT",
    "FOUNDRY_CANDIDATES",
    "PBR_CHANNELS",
    "cook_validate_material_foundry",
    "validate_material_foundry_stage",
    "validate_foundry_spec",
]
