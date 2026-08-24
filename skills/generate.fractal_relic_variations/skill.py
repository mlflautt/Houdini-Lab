"""Bounded plan for local PDG relic variations and an editable comparison gallery."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "generate.fractal_relic_variations"
SKILL_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,27}\Z")


def plan(
    source_node_path: str,
    artifact_dir: str,
    run_id: str = "relic_variations_001",
    base_seed: int = 1001,
    count: int = 9,
    seed_step: int = 97,
    radius_min: float = 0.8,
    radius_max: float = 1.2,
    noise_min: float = 0.1,
    noise_max: float = 0.28,
    iterations: int = 4,
    detail_level: str = "preview",
    candidate_index: int = 0,
    viewer_name: str = "",
    viewport_name: str = "",
) -> list[dict[str, Any]]:
    """Return exact commands for build, generation, local cook, gallery, and observation."""
    if not source_node_path.startswith("/") or source_node_path == "/":
        raise ValueError("source_node_path must be an absolute SOP node path")
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-28 filename-safe characters")
    if not 2 <= count <= 16:
        raise ValueError("skill count must be between 2 and 16 local work items")
    if bool(viewer_name) != bool(viewport_name):
        raise ValueError("viewer_name and viewport_name must be supplied together")

    safe_run = run_id.upper().replace("-", "_")
    network_name = f"HERMES_PDG_{safe_run}"[:48]
    gallery_name = f"HERMES_GALLERY_{safe_run}"[:48]
    camera_name = f"CAM_{safe_run}"[:48]
    topnet_path = f"/tasks/{network_name}"
    gallery_path = f"/obj/{gallery_name}"
    gallery_output = f"{gallery_path}/OUT_GALLERY"
    camera_path = f"/obj/{camera_name}"
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    manifest_dir = artifacts / "manifests"
    observation_dir = artifacts / "observations"
    scene_dir = artifacts / "scenes"
    geometry_dir = artifacts / "geometry"
    manifest_path = manifest_dir / f"{run_id}_variation_plan.json"
    result_path = manifest_dir / f"{run_id}_variation_results.json"
    scene_path = scene_dir / f"{run_id}_pdg_source.hipnc"
    top_graph_svg = observation_dir / f"{run_id}_top_graph.svg"
    gallery_graph_svg = observation_dir / f"{run_id}_gallery_graph.svg"
    gallery_manifest = manifest_dir / f"{run_id}_gallery_manifest.json"
    preview_path = observation_dir / f"{run_id}_contact_sheet.png"

    seconds_per_item = 30.0
    worker_memory = 2_147_483_648
    max_points_per_item = 50_000
    max_primitives_per_item = 50_000
    max_output_bytes = count * 25_000_000
    common = {
        "session_id": run_id,
        "project_id": SKILL_ID,
        "expected": {"skill": SKILL_ID, "skill_version": SKILL_VERSION, "run_id": run_id},
    }
    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=90,
        max_points=max_points_per_item,
        max_primitives=max_primitives_per_item,
        max_memory_bytes=worker_memory,
        max_work_items=count,
        max_output_bytes=max_output_bytes,
    )
    pdg_policy = Policy(
        risk=RiskClass.MEDIUM,
        allow_external_process=True,
        max_seconds=count * seconds_per_item,
        max_points=max_points_per_item,
        max_primitives=max_primitives_per_item,
        max_memory_bytes=worker_memory,
        max_work_items=count,
        max_output_bytes=max_output_bytes,
    )
    gallery_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=30,
        max_points=count * max_points_per_item,
        max_primitives=count * max_primitives_per_item,
        max_memory_bytes=536_870_912,
    )
    calls = [
        build_envelope(
            "pdg.variation.build",
            {
                "source_node_path": source_node_path,
                "output_dir": str(geometry_dir),
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_pdg_build.jsonl"),
                "network_name": network_name,
                "base_seed": base_seed,
                "count": count,
                "seed_step": seed_step,
                "base_radius_range": [radius_min, radius_max],
                "noise_amplitude_range": [noise_min, noise_max],
                "iterations": iterations,
                "detail_level": detail_level,
                "candidate_index": candidate_index,
                "scheduler_seconds_per_item": seconds_per_item,
                "scheduler_memory_mb": worker_memory // 1_048_576,
            },
            request_id=f"{run_id}-pdg-build",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "pdg.variation.generate",
            {"topnet_path": topnet_path, "output_path": str(manifest_path)},
            request_id=f"{run_id}-pdg-generate",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "pdg.variation.cook",
            {
                "topnet_path": topnet_path,
                "manifest_path": str(manifest_path),
                "result_path": str(result_path),
                "scene_path": str(scene_path),
                "log_path": str(log_dir / f"{run_id}_pdg_cook.jsonl"),
                "estimate": {
                    "work_items": count,
                    "seconds_per_item": seconds_per_item,
                    "points_per_item": max_points_per_item,
                    "primitives_per_item": max_primitives_per_item,
                    "memory_bytes_per_item": worker_memory,
                    "output_bytes_total": max_output_bytes,
                },
            },
            request_id=f"{run_id}-pdg-cook",
            policy=pdg_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "pdg.variation.build_gallery",
            {
                "result_path": str(result_path),
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_gallery_build.jsonl"),
                "gallery_name": gallery_name,
                "camera_name": camera_name,
                "spacing": 5.0,
            },
            request_id=f"{run_id}-gallery-build",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "cook.node",
            {
                "node_path": gallery_output,
                "scope": "display_chain",
                "frame": None,
                "force": True,
                "estimate": {
                    "points": count * max_points_per_item,
                    "primitives": count * max_primitives_per_item,
                    "memory_bytes": 536_870_912,
                    "seconds": 30,
                },
                "log_path": str(log_dir / f"{run_id}_gallery_cook.jsonl"),
            },
            request_id=f"{run_id}-gallery-cook",
            policy=gallery_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "geometry.validate",
            {
                "node_path": gallery_output,
                "expectations": {
                    "min_points": count,
                    "max_points": count * max_points_per_item,
                    "min_primitives": count,
                    "max_primitives": count * max_primitives_per_item,
                    "require_finite_bounds": True,
                    "allow_warnings": False,
                },
            },
            request_id=f"{run_id}-gallery-validate",
            policy=gallery_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_svg",
            {"node_path": topnet_path, "output_path": str(top_graph_svg), "max_nodes": 32},
            request_id=f"{run_id}-top-svg",
            policy=gallery_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_svg",
            {
                "node_path": gallery_path,
                "output_path": str(gallery_graph_svg),
                "max_nodes": 96,
            },
            request_id=f"{run_id}-gallery-svg",
            policy=gallery_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_manifest",
            {
                "node_path": gallery_path,
                "output_path": str(gallery_manifest),
                "public_parameters": {},
                "metric_node_paths": [gallery_output],
                "metadata": {
                    "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
                    "source_variation_result": str(result_path),
                    "selection": {"method": "human", "winner": None, "automatic_ranking": False},
                    "contact_sheet": str(preview_path) if viewer_name else None,
                },
            },
            request_id=f"{run_id}-gallery-manifest",
            policy=gallery_policy,
            **common,
        ).as_dict(),
    ]
    if viewer_name:
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
                request_id=f"{run_id}-contact-sheet",
                policy=gallery_policy,
                **common,
            ).as_dict()
        )
    calls.append(
        build_envelope(
            "hip.save_snapshot",
            {"output_dir": str(scene_dir), "stem": f"{run_id}_final"},
            request_id=f"{run_id}-final-snapshot",
            policy=gallery_policy,
            **common,
        ).as_dict()
    )
    return calls


__all__ = ["SKILL_ID", "SKILL_VERSION", "plan"]
