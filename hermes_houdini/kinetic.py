"""Native and optional-MOPs kinetic reliquary planning and live validation."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from . import get_hou
from .cook import geometry_metrics
from .execution import current_envelope

MOPS_KINETIC_NODE_TYPES = (
    "MOPS::Plain_Falloff::1.0",
    "MOPS::Noise_Falloff::1.4",
    "MOPS::Shape_Falloff::1.5",
    "MOPS::Transform_Modifier::1.1",
)
KINETIC_VARIANTS = ("native", "mops_plain", "mops_noise", "mops_shape")


def detect_mops_capability(node_type_names: Iterable[str]) -> dict[str, Any]:
    available = {str(name) for name in node_type_names}
    missing = [name for name in MOPS_KINETIC_NODE_TYPES if name not in available]
    return {
        "available": not missing,
        "required_node_types": list(MOPS_KINETIC_NODE_TYPES),
        "missing_node_types": missing,
        "scope": "four_exact_mops_1_12_sop_types_only",
    }


def validate_kinetic_spec(
    *, seed: int, copy_count: int, start_frame: int, end_frame: int, mops_available: bool
) -> dict[str, Any]:
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 2_147_483_647:
        raise ValueError("seed must be an integer between 0 and 2147483647")
    if not isinstance(copy_count, int) or isinstance(copy_count, bool) or not 8 <= copy_count <= 64:
        raise ValueError("copy_count must be an integer between 8 and 64")
    if (
        not isinstance(start_frame, int)
        or not isinstance(end_frame, int)
        or start_frame < 1
        or end_frame <= start_frame
        or end_frame - start_frame > 48
    ):
        raise ValueError("frame range must be increasing, start at 1+, and span at most 48 frames")
    if not isinstance(mops_available, bool):
        raise ValueError("mops_available must be boolean")
    middle = start_frame + ((end_frame - start_frame) // 2)
    candidates = []
    for variant in KINETIC_VARIANTS:
        available = variant == "native" or mops_available
        candidates.append(
            {
                "id": variant,
                "available": available,
                "seed": seed,
                "human_rating": {"score": None, "notes": ""},
                "automatic_rank": None,
            }
        )
    return {
        "schema": "hermes.houdini.kinetic_reliquary_spec",
        "schema_version": "1.0",
        "seed": seed,
        "copy_count": copy_count,
        "frame_range": [start_frame, end_frame],
        "sample_frames": [start_frame, middle, end_frame],
        "mops": {
            "id": "mops-1.12",
            "available": mops_available,
            "required_node_types": list(MOPS_KINETIC_NODE_TYPES),
            "fallback": "native_graph_plus_OPTIONAL_MOPS_UNAVAILABLE_contract",
        },
        "candidates": candidates,
        "selection": {"method": "human", "winner": None, "automatic_ranking": False},
    }


def _safe_node_path(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("/") or ".." in value.split("/"):
        raise ValueError(f"{label} must be an absolute Houdini node path")
    return value


def _geometry_digest(geometry: Any) -> str:
    payload: dict[str, Any] = {}
    for name in ("P", "orient", "scale", "v"):
        attribute = geometry.findPointAttrib(name)
        if attribute is None:
            raise ValueError(f"kinetic geometry is missing point attribute {name}")
        payload[name] = [round(float(value), 7) for value in geometry.pointFloatAttribValues(name)]
    payload["variant_id"] = list(geometry.pointStringAttribValues("variant_id"))
    payload["seed"] = list(geometry.pointIntAttribValues("seed"))
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def cook_validate_kinetic_reliquary(
    *,
    network_path: str,
    base_packed_path: str,
    native_path: str,
    selector_path: str,
    selected_path: str,
    comparison_path: str,
    seed: int,
    copy_count: int,
    start_frame: int,
    end_frame: int,
    mops_available: bool,
    output_path: str,
    branch_paths: dict[str, str] | None = None,
    unavailable_path: str = "",
    max_points: int = 20_000,
    max_primitives: int = 20_000,
    max_seconds: float = 120.0,
) -> dict[str, Any]:
    hou = get_hou()
    spec = validate_kinetic_spec(
        seed=seed,
        copy_count=copy_count,
        start_frame=start_frame,
        end_frame=end_frame,
        mops_available=mops_available,
    )
    output = Path(output_path).expanduser()
    if not output.is_absolute() or output.suffix.lower() != ".json":
        raise ValueError("output_path must be an absolute JSON path")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite validation artifact: {output}")
    network = hou.node(_safe_node_path(network_path, "network_path"))
    if network is None or network.type().category().name() != "Object":
        raise ValueError("kinetic network must be an Object node")
    fixed_paths = {
        "base_packed": base_packed_path,
        "native": native_path,
        "selector": selector_path,
        "selected": selected_path,
        "comparison": comparison_path,
    }
    fixed = {
        key: hou.node(_safe_node_path(value, f"{key}_path")) for key, value in fixed_paths.items()
    }
    if any(node is None or node.parent() != network for node in fixed.values()):
        raise ValueError("kinetic graph has missing or foreign fixed contract nodes")
    if int(fixed["selector"].parm("input").eval()) != 0:
        raise ValueError("kinetic selector must default to the native branch")
    capability = detect_mops_capability(hou.sopNodeTypeCategory().nodeTypes())
    if mops_available and not capability["available"]:
        raise ValueError(f"MOPs requested but unavailable: {capability['missing_node_types']}")

    paths = {"native": native_path}
    if mops_available:
        expected_branches = {"mops_plain", "mops_noise", "mops_shape"}
        if not isinstance(branch_paths, dict) or set(branch_paths) != expected_branches:
            raise ValueError("branch_paths must declare the three exact MOPs variants")
        expected_types = {
            "plain_falloff": MOPS_KINETIC_NODE_TYPES[0],
            "plain_transform": MOPS_KINETIC_NODE_TYPES[3],
            "noise_falloff": MOPS_KINETIC_NODE_TYPES[1],
            "noise_transform": MOPS_KINETIC_NODE_TYPES[3],
            "shape_falloff": MOPS_KINETIC_NODE_TYPES[2],
            "shape_transform": MOPS_KINETIC_NODE_TYPES[3],
        }
        expected_roles = {key: f"kinetic_mops_{key}" for key in expected_types}
        by_role = {child.userData("hermes_role"): child for child in network.children()}
        for key, node_type in expected_types.items():
            node = by_role.get(expected_roles[key])
            if node is None or node.type().name() != node_type:
                raise ValueError(f"MOPs node contract failed: {key}")
        paths.update(branch_paths)
    else:
        unavailable = hou.node(_safe_node_path(unavailable_path, "unavailable_path"))
        if unavailable is None or unavailable.parent() != network:
            raise ValueError("plugin-disabled graph lacks OPTIONAL_MOPS_UNAVAILABLE")
        if unavailable.userData("hermes_role") != "kinetic_mops_unavailable":
            raise ValueError("plugin-disabled graph has a stale unavailable role")

    started = time.monotonic()
    original_frame = hou.frame()
    branch_results: dict[str, Any] = {}
    try:
        for variant, node_path in paths.items():
            node = hou.node(_safe_node_path(node_path, variant))
            if node is None or node.parent() != network:
                raise ValueError(f"kinetic branch missing: {variant}")
            samples = []
            digests = []
            for frame in spec["sample_frames"]:
                hou.setFrame(frame)
                node.cook(force=True)
                errors = list(node.errors())
                warnings = list(node.warnings())
                if errors or warnings:
                    raise ValueError(f"kinetic {variant} frame {frame} has Houdini messages")
                geometry = node.geometry()
                metrics = geometry_metrics(node)
                if metrics["points"] != copy_count or metrics["primitives"] != copy_count:
                    raise ValueError(f"kinetic {variant} does not preserve one packed piece per copy")
                required = {"P", "orient", "scale", "v", "seed", "variant_id"}
                missing = required.difference(metrics["point_attributes"])
                if missing:
                    raise ValueError(f"kinetic {variant} missing attributes: {sorted(missing)}")
                variants = set(geometry.pointStringAttribValues("variant_id"))
                seeds = set(geometry.pointIntAttribValues("seed"))
                if variants != {variant} or seeds != {seed}:
                    raise ValueError(f"kinetic {variant} provenance attributes are stale")
                digest = _geometry_digest(geometry)
                digests.append(digest)
                bounds = geometry.boundingBox()
                samples.append(
                    {
                        "frame": frame,
                        "digest": digest,
                        "bounds_min": list(bounds.minvec()),
                        "bounds_max": list(bounds.maxvec()),
                        "metrics": metrics,
                    }
                )
                if metrics["points"] > max_points or metrics["primitives"] > max_primitives:
                    raise ValueError("kinetic branch exceeds geometry policy budget")
            if len(set(digests)) != len(digests):
                raise ValueError(f"kinetic {variant} lacks deterministic temporal change")
            branch_results[variant] = {"samples": samples, "human_rating": None, "automatic_rank": None}

        hou.setFrame(spec["sample_frames"][-1])
        fixed["comparison"].cook(force=True)
        comparison_metrics = geometry_metrics(fixed["comparison"])
        if comparison_metrics["points"] <= 0 or comparison_metrics["primitives"] <= 0:
            raise ValueError("kinetic presentation comparison is empty")
        if comparison_metrics["points"] > max_points or comparison_metrics["primitives"] > max_primitives:
            raise ValueError("kinetic presentation comparison exceeds geometry policy budget")
    finally:
        hou.setFrame(original_frame)

    if time.monotonic() - started > max_seconds:
        raise TimeoutError("kinetic validation exceeded max_seconds")
    document = {
        "schema": "hermes.houdini.kinetic_reliquary_validation",
        "schema_version": "1.0",
        "status": "success",
        "houdini": {"build": hou.applicationVersionString(), "license": hou.licenseCategory().name()},
        "request": current_envelope().as_dict() if current_envelope() else None,
        "capability": capability,
        "spec": spec,
        "branches": branch_results,
        "comparison_metrics": comparison_metrics,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "selection": spec["selection"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "artifact": str(output),
        "capability": capability,
        "branches": branch_results,
        "comparison_metrics": comparison_metrics,
        "selection": spec["selection"],
    }


def validate_kinetic_stage(*, stage_node_path: str, prim_path: str, max_prims: int = 10_000) -> dict[str, Any]:
    hou = get_hou()
    node = hou.node(_safe_node_path(stage_node_path, "stage_node_path"))
    if node is None or node.type().category().name() != "Lop":
        raise ValueError("kinetic stage contract is missing")
    stage = node.stage()
    if stage is None:
        raise ValueError("kinetic USD stage did not compose")
    prim = stage.GetPrimAtPath(_safe_node_path(prim_path, "prim_path"))
    if not prim or not prim.IsValid():
        raise ValueError("kinetic USD root is missing")
    prim_count = sum(1 for _ in stage.Traverse())
    if prim_count > max_prims:
        raise ValueError("kinetic USD stage exceeds max_prims")
    if list(node.errors()) or list(node.warnings()):
        raise ValueError("kinetic USD stage has Houdini messages")
    return {
        "stage_node_path": node.path(),
        "prim_path": prim_path,
        "prim_count": prim_count,
        "selection": {"winner": None, "automatic_ranking": False},
    }


def cook_validate_kinetic_presentation(
    *,
    network_path: str,
    presentation_path: str,
    start_frame: int,
    end_frame: int,
    mops_available: bool,
    output_path: str,
    max_points: int = 20_000,
    max_primitives: int = 20_000,
    max_seconds: float = 120.0,
) -> dict[str, Any]:
    """Validate the layered presentation after, without replacing, packed branch contracts."""
    hou = get_hou()
    if not isinstance(mops_available, bool):
        raise ValueError("mops_available must be boolean")
    if (
        not isinstance(start_frame, int)
        or not isinstance(end_frame, int)
        or start_frame < 1
        or end_frame <= start_frame
        or end_frame - start_frame > 48
    ):
        raise ValueError("frame range must be increasing, start at 1+, and span at most 48 frames")
    output = Path(output_path).expanduser()
    if not output.is_absolute() or output.suffix.lower() != ".json":
        raise ValueError("output_path must be an absolute JSON path")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite validation artifact: {output}")
    network = hou.node(_safe_node_path(network_path, "network_path"))
    presentation = hou.node(_safe_node_path(presentation_path, "presentation_path"))
    if network is None or network.type().category().name() != "Object":
        raise ValueError("kinetic presentation network must be an Object node")
    if presentation is None or presentation.parent() != network:
        raise ValueError("kinetic staged presentation contract is missing or foreign")
    if presentation.userData("hermes_role") != "kinetic_staged_contract":
        raise ValueError("kinetic staged presentation role is stale")
    roles = {child.userData("hermes_role") for child in network.children()}
    required_roles = (
        {
            "kinetic_staged_native_face",
            "kinetic_staged_plain_face",
            "kinetic_staged_noise_face",
            "kinetic_staged_shape_face",
            "kinetic_staged_native_inner_xform",
            "kinetic_staged_plain_inner_xform",
            "kinetic_staged_noise_inner_xform",
            "kinetic_staged_shape_inner_xform",
        }
        if mops_available
        else {"kinetic_staged_native_only_face", "kinetic_staged_native_only_inner_xform"}
    )
    missing_roles = required_roles.difference(roles)
    if missing_roles:
        raise ValueError(f"kinetic staged presentation roles are missing: {sorted(missing_roles)}")

    middle = start_frame + ((end_frame - start_frame) // 2)
    sample_frames = [start_frame, middle, end_frame]
    started = time.monotonic()
    original_frame = hou.frame()
    samples = []
    digests = []
    try:
        for frame in sample_frames:
            hou.setFrame(frame)
            presentation.cook(force=True)
            if list(presentation.errors()) or list(presentation.warnings()):
                raise ValueError(f"kinetic staged presentation frame {frame} has Houdini messages")
            metrics = geometry_metrics(presentation)
            if not metrics["points"] or not metrics["primitives"]:
                raise ValueError("kinetic staged presentation is empty")
            if metrics["points"] > max_points or metrics["primitives"] > max_primitives:
                raise ValueError("kinetic staged presentation exceeds geometry policy budget")
            if "Cd" not in metrics["point_attributes"]:
                raise ValueError("kinetic staged presentation lacks point color identity")
            geometry = presentation.geometry()
            bounds = geometry.boundingBox()
            size = bounds.sizevec()
            min_width = 18.0 if mops_available else 4.0
            if float(size[0]) < min_width or float(size[1]) < 4.0:
                raise ValueError("kinetic staged presentation remains a flat or undersized strip")
            payload = {
                "P": [round(float(value), 7) for value in geometry.pointFloatAttribValues("P")],
                "Cd": [round(float(value), 7) for value in geometry.pointFloatAttribValues("Cd")],
            }
            digest = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            digests.append(digest)
            samples.append(
                {
                    "frame": frame,
                    "digest": digest,
                    "bounds_min": list(bounds.minvec()),
                    "bounds_max": list(bounds.maxvec()),
                    "bounds_size": list(size),
                    "metrics": metrics,
                }
            )
    finally:
        hou.setFrame(original_frame)
    elapsed = time.monotonic() - started
    if elapsed > max_seconds:
        raise TimeoutError("kinetic staged presentation validation exceeded max_seconds")
    if len(set(digests)) != len(digests):
        raise ValueError("kinetic staged presentation lacks temporal change")
    document = {
        "schema": "hermes.houdini.kinetic_reliquary_presentation_validation",
        "schema_version": "1.0",
        "status": "success",
        "houdini": {"build": hou.applicationVersionString(), "license": hou.licenseCategory().name()},
        "request": current_envelope().as_dict() if current_envelope() else None,
        "mops_available": mops_available,
        "sample_frames": sample_frames,
        "samples": samples,
        "elapsed_seconds": round(elapsed, 6),
        "selection": {"winner": None, "automatic_ranking": False},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"artifact": str(output), **document}


__all__ = [
    "KINETIC_VARIANTS",
    "MOPS_KINETIC_NODE_TYPES",
    "cook_validate_kinetic_reliquary",
    "cook_validate_kinetic_presentation",
    "detect_mops_capability",
    "validate_kinetic_spec",
    "validate_kinetic_stage",
]
