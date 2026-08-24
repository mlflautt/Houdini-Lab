"""Plan a bounded native Vellum relic-drop simulation and temporal verification run."""

from __future__ import annotations

import math
import re
from pathlib import Path

from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "simulate.vellum_relic_drop"
SKILL_VERSION = "1.0.0"
RECIPE_ID = "sop.vellum_relic_drop"
RECIPE_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,27}\Z")


def _frame_count(start_frame: float, end_frame: float, frame_step: float) -> int:
    if any(not math.isfinite(value) for value in (start_frame, end_frame, frame_step)):
        raise ValueError("frame range values must be finite")
    if frame_step <= 0:
        raise ValueError("frame_step must be greater than zero")
    if end_frame < start_frame:
        raise ValueError("end_frame must be greater than or equal to start_frame")
    return int(math.floor(((end_frame - start_frame) / frame_step) + 1e-9)) + 1


def plan(
    parent_node_id: str,
    artifact_dir: str,
    run_id: str = "vellum_drop_001",
    start_frame: float = 1.0,
    end_frame: float = 24.0,
    frame_step: float = 1.0,
    drop_height: float = 2.5,
    mass: float = 0.1,
    thickness: float = 0.04,
    stretch_stiffness: float = 1.0,
    stretch_exponent: int = 5,
    bend_stiffness: float = 1.0,
    bend_exponent: int = -1,
    substeps: int = 2,
    constraint_iterations: int = 50,
    viewer_name: str = "",
    viewport_name: str = "",
    camera_path: str = "",
) -> list[dict[str, object]]:
    """Return checkpointed graph, temporal cook, validation, observation, and snapshot calls."""
    if not parent_node_id.startswith("/") or parent_node_id == "/":
        raise ValueError("parent_node_id must be an absolute SOP network path")
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-28 filename-safe characters")
    frames = _frame_count(start_frame, end_frame, frame_step)
    if frames > 48:
        raise ValueError("this skill is bounded to at most 48 frames")
    viewer_values = (viewer_name, viewport_name, camera_path)
    if any(viewer_values) and not all(viewer_values):
        raise ValueError("viewer_name, viewport_name, and camera_path must be provided together")

    run_code = run_id.upper().replace("-", "_")
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    cache_dir = artifacts / "cache" / run_id / "v001"
    cache_path = cache_dir / f"{run_id}.$F4.bgeo.sc"
    graph_log = log_dir / f"{run_id}_graph.jsonl"
    cook_log = log_dir / f"{run_id}_temporal_cook.jsonl"
    graph_svg = observation_dir / f"{run_id}_graph.svg"
    graph_manifest = manifest_dir / f"{run_id}_graph_manifest.json"
    preview_path = observation_dir / f"{run_id}_frame_{end_frame:g}.png"
    compare_path = f"{parent_node_id.rstrip('/')}/OUT_{run_code}_COMPARE"
    sim_cache_path = f"{parent_node_id.rstrip('/')}/OUT_{run_code}_CACHE"
    rest_path = f"{parent_node_id.rstrip('/')}/OUT_{run_code}_REST"
    collider_path = f"{parent_node_id.rstrip('/')}/OUT_{run_code}_COLLIDER"
    solver_path = f"{parent_node_id.rstrip('/')}/{run_code}_SOLVER"
    cache_node_path = f"{parent_node_id.rstrip('/')}/{run_code}_FILE_CACHE"

    max_points = 50_000
    max_primitives = 50_000
    max_memory = 536_870_912
    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=30,
        max_points=max_points,
        max_primitives=max_primitives,
        max_memory_bytes=max_memory,
        max_frames=frames,
    )
    cook_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=90,
        max_points=max_points,
        max_primitives=max_primitives,
        max_memory_bytes=max_memory,
        max_frames=frames,
    )
    common = {
        "session_id": run_id,
        "project_id": SKILL_ID,
        "expected": {"skill": SKILL_ID, "skill_version": SKILL_VERSION, "run_id": run_id},
    }
    recipe_inputs = {
        "run_code": run_code,
        "lineage": f"{SKILL_ID}@{SKILL_VERSION} run={run_id}",
        "start_frame": start_frame,
        "end_frame": end_frame,
        "frame_step": frame_step,
        "drop_height": drop_height,
        "mass": mass,
        "thickness": thickness,
        "stretch_stiffness": stretch_stiffness,
        "stretch_exponent": stretch_exponent,
        "bend_stiffness": bend_stiffness,
        "bend_exponent": bend_exponent,
        "substeps": substeps,
        "constraint_iterations": constraint_iterations,
        "cache_path": str(cache_path),
    }
    metadata = {
        "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
        "recipe": {"id": RECIPE_ID, "version": RECIPE_VERSION},
        "run_id": run_id,
        "temporal_contract": {
            "frames": [start_frame, end_frame, frame_step],
            "frame_count": frames,
            "cook_log": str(cook_log),
            "stateful": True,
        },
        "cache_contract": {
            "node_path": cache_node_path,
            "path": str(cache_path),
            "format": ".bgeo.sc",
            "write_implicit": False,
            "status": "configured_not_written",
        },
        "license": {
            "mode": "houdini-apprentice-noncommercial",
            "commercial_use": False,
            "scene_extension": ".hipnc",
            "render_ceiling": [1280, 720],
        },
        "selection": {"method": "human", "winner": None, "automatic_ranking": False},
        "outputs": {"simulation": sim_cache_path, "comparison": compare_path},
    }
    calls = [
        build_envelope(
            "recipe.instantiate",
            {
                "recipe_id": RECIPE_ID,
                "version": RECIPE_VERSION,
                "parent_path": parent_node_id,
                "batch_id": f"{SKILL_ID}:{run_id}",
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(graph_log),
                "inputs": recipe_inputs,
                "label": f"Hermes {SKILL_ID} {run_id}",
                "checkpoint_stem": f"vellum_{run_id}",
            },
            request_id=f"{run_id}-graph",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "cook.node",
            {
                "node_path": sim_cache_path,
                "scope": "frame_range",
                "frame": None,
                "frame_range": [start_frame, end_frame, frame_step],
                "force": True,
                "estimate": {
                    "points": 1000,
                    "primitives": 1000,
                    "memory_bytes": 268_435_456,
                    "seconds": 60.0,
                },
                "log_path": str(cook_log),
            },
            request_id=f"{run_id}-temporal-cook",
            policy=cook_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "geometry.validate",
            {
                "node_path": rest_path,
                "expectations": {
                    "min_points": 10,
                    "max_points": 1000,
                    "min_primitives": 10,
                    "max_primitives": 1000,
                    "require_finite_bounds": True,
                    "allow_warnings": False,
                },
            },
            request_id=f"{run_id}-rest-validate",
            policy=cook_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "geometry.validate",
            {
                "node_path": collider_path,
                "expectations": {
                    "min_points": 8,
                    "max_points": 8,
                    "min_primitives": 6,
                    "max_primitives": 6,
                    "require_finite_bounds": True,
                    "allow_warnings": False,
                },
            },
            request_id=f"{run_id}-collider-validate",
            policy=cook_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_svg",
            {"node_path": parent_node_id, "output_path": str(graph_svg), "max_nodes": 32},
            request_id=f"{run_id}-graph-svg",
            policy=cook_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_manifest",
            {
                "node_path": parent_node_id,
                "output_path": str(graph_manifest),
                "public_parameters": {
                    solver_path: ["substeps", "niter", "smoothiter", "gravityy"],
                    cache_node_path: ["file", "trange", "f1", "f2", "f3", "initsim"],
                },
                "metric_node_paths": [rest_path, collider_path],
                "metadata": metadata,
            },
            request_id=f"{run_id}-manifest",
            policy=cook_policy,
            **common,
        ).as_dict(),
    ]
    if all(viewer_values):
        calls.append(
            build_envelope(
                "viewport.capture",
                {
                    "viewer_name": viewer_name,
                    "viewport_name": viewport_name,
                    "camera_path": camera_path,
                    "output_path": str(preview_path),
                    "frame": end_frame,
                    "width": 1280,
                    "height": 720,
                },
                request_id=f"{run_id}-viewport",
                policy=cook_policy,
                **common,
            ).as_dict()
        )
    calls.append(
        build_envelope(
            "hip.save_snapshot",
            {"output_dir": str(scene_dir), "stem": f"vellum_{run_id}_final"},
            request_id=f"{run_id}-snapshot",
            policy=cook_policy,
            **common,
        ).as_dict()
    )
    return calls


__all__ = ["plan"]
