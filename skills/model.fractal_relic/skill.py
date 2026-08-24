"""Executable plan for the graph-first ``model.fractal_relic`` skill.

The plan builds three comparable native-SOP candidates in one approved graph batch,
cooks only the explicit comparison output, validates the cooked data, and records graph,
geometry, lineage, rating slots, and a final non-commercial HIP snapshot. It never
generates VEX/Python SOP code and never selects a winning candidate.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from hermes_houdini.ids import make_id
from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import attribute_contract, build_envelope
from skills._lib.fractal_relic import build_graph_spec

SKILL_ID = "model.fractal_relic"
SKILL_VERSION = "1.1.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}\Z")


def plan(
    parent_node_id: str,
    artifact_dir: str,
    run_id: str = "fractal_relic_001",
    seed: int = 42,
    iterations: int = 4,
    detail_level: str = "preview",
    base_radius: float = 1.0,
    detail_radius: float = 0.08,
    noise_amplitude: float = 0.16,
    preview_candidate: int = 0,
    viewer_name: str = "",
    viewport_name: str = "",
    camera_path: str = "",
) -> list[dict[str, Any]]:
    """Return ordered, bounded commands for one complete relic run."""
    if not parent_node_id.startswith("/") or parent_node_id == "/":
        raise ValueError("parent_node_id must be an absolute SOP network path")
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-40 filename-safe characters")
    viewer_values = (viewer_name, viewport_name, camera_path)
    if any(viewer_values) and not all(viewer_values):
        raise ValueError("viewer_name, viewport_name, and camera_path must be provided together")

    batch_id = f"fractal_relic:{run_id}"
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    graph_log = log_dir / f"{run_id}_graph.jsonl"
    cook_log = log_dir / f"{run_id}_cook.jsonl"
    graph_svg = observation_dir / f"{run_id}_graph.svg"
    graph_manifest = manifest_dir / f"{run_id}_graph_manifest.json"
    preview_path = observation_dir / f"{run_id}_comparison.png"
    checkpoint_stem = f"relic_{run_id}"

    graph_spec = build_graph_spec(
        parent_path=parent_node_id,
        seed=seed,
        iterations=iterations,
        detail_level=detail_level,
        base_radius=base_radius,
        detail_radius=detail_radius,
        noise_amplitude=noise_amplitude,
        preview_candidate=preview_candidate,
    )
    operations = graph_spec["operations"]
    candidates = graph_spec["candidates"]
    for candidate in candidates:
        candidate["output_hermes_id"] = make_id("Sop", f"{batch_id}:{candidate['refs']['out']}")
    comparison_path = graph_spec["comparison_path"]
    selected_path = graph_spec["selected_path"]
    public_parameters = graph_spec["public_parameters"]

    metadata = {
        "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
        "run_id": run_id,
        "license": {
            "mode": "houdini-apprentice-noncommercial",
            "commercial_use": False,
            "scene_extension": ".hipnc",
        },
        "controls": {
            "seed": seed,
            "iterations": iterations,
            "detail_level": detail_level,
            "base_radius": base_radius,
            "detail_radius": detail_radius,
            "noise_amplitude": noise_amplitude,
            "preview_candidate": preview_candidate,
        },
        "selection": {
            "method": "human",
            "preview_input": preview_candidate,
            "winner": None,
            "automatic_ranking": False,
        },
        "candidates": candidates,
        "outputs": {
            "comparison_node": comparison_path,
            "selected_node": selected_path,
            "graph_svg": str(graph_svg),
            "viewport_preview": str(preview_path) if all(viewer_values) else None,
            "graph_replay_log": str(graph_log),
            "cook_log": str(cook_log),
        },
        "attribute_contract": attribute_contract(),
    }
    max_points = 3_000_000
    max_primitives = 3_000_000
    max_memory = 536_870_912
    common = {
        "session_id": run_id,
        "project_id": SKILL_ID,
        "expected": {"skill": SKILL_ID, "skill_version": SKILL_VERSION, "run_id": run_id},
    }
    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=90,
        max_points=max_points,
        max_primitives=max_primitives,
        max_memory_bytes=max_memory,
    )
    cook_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=90,
        max_points=max_points,
        max_primitives=max_primitives,
        max_memory_bytes=max_memory,
    )
    estimated_instances = sum(candidate["mutations"]["point_count"] for candidate in candidates)
    calls = [
        build_envelope(
            "graph.apply_batch",
            {
                "batch_id": batch_id,
                "operations": operations,
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(graph_log),
                "label": f"Hermes {SKILL_ID} {run_id}",
                "checkpoint_stem": checkpoint_stem,
            },
            request_id=f"{run_id}-graph",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "cook.node",
            {
                "node_path": comparison_path,
                "scope": "display_chain",
                "frame": None,
                "force": False,
                "estimate": {
                    "points": estimated_instances * 4 + 20_000,
                    "primitives": estimated_instances * 4 + 20_000,
                    "memory_bytes": min(max_memory, estimated_instances * 32_768 + 20_000_000),
                    "seconds": 45.0,
                },
                "log_path": str(cook_log),
            },
            request_id=f"{run_id}-cook",
            policy=cook_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "geometry.validate",
            {
                "node_path": comparison_path,
                "expectations": {
                    "min_points": 3,
                    "max_points": max_points,
                    "min_primitives": 3,
                    "max_primitives": max_primitives,
                    "require_finite_bounds": True,
                    "allow_warnings": False,
                },
            },
            request_id=f"{run_id}-validate",
            policy=cook_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_svg",
            {
                "node_path": parent_node_id,
                "output_path": str(graph_svg),
                "max_nodes": 64,
            },
            request_id=f"{run_id}-graph-svg",
            policy=cook_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_manifest",
            {
                "node_path": parent_node_id,
                "output_path": str(graph_manifest),
                "public_parameters": public_parameters,
                "metric_node_paths": [comparison_path],
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
                    "frame": 1,
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
            {"output_dir": str(scene_dir), "stem": f"{checkpoint_stem}_final"},
            request_id=f"{run_id}-snapshot",
            policy=cook_policy,
            **common,
        ).as_dict()
    )
    return calls


def attribute_contract_doc() -> dict[str, Any]:
    return attribute_contract()


__all__ = ["SKILL_ID", "SKILL_VERSION", "attribute_contract_doc", "plan"]
