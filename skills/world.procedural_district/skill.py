"""Plan a bounded native-SOP, native-TOP procedural district workflow."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "world.procedural_district"
SKILL_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,27}\Z")


def plan(
    artifact_dir: str,
    run_id: str = "district_001",
    base_seed: int = 1601,
    lot_count: int = 12,
    seed_step: int = 53,
    columns: int = 4,
    lot_spacing: float = 6.0,
    viewer_name: str = "",
    viewport_name: str = "",
) -> list[dict[str, Any]]:
    """Return exact build, generation, cook, assembly, validation, and evidence commands."""
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-28 filename-safe characters")
    if not isinstance(lot_count, int) or isinstance(lot_count, bool) or not 4 <= lot_count <= 16:
        raise ValueError("lot_count must be between 4 and 16")
    if not isinstance(columns, int) or isinstance(columns, bool) or not 2 <= columns <= 4:
        raise ValueError("columns must be between 2 and 4")
    if not isinstance(lot_spacing, (int, float)) or isinstance(lot_spacing, bool):
        raise ValueError("lot_spacing must be numeric")
    if not 5.5 <= float(lot_spacing) <= 20.0:
        raise ValueError("lot_spacing must be between 5.5 and 20")
    if bool(viewer_name) != bool(viewport_name):
        raise ValueError("viewer_name and viewport_name must be supplied together")

    safe = run_id.upper().replace("-", "_")
    source_name = f"HERMES_DISTRICT_SRC_{safe}"[:48]
    network_name = f"HERMES_PDG_DISTRICT_{safe}"[:48]
    assembly_name = f"HERMES_DISTRICT_{safe}"[:48]
    camera_name = f"CAM_DISTRICT_{safe}"[:48]
    source_path = f"/obj/{source_name}"
    topnet_path = f"/tasks/{network_name}"
    assembly_path = f"/obj/{assembly_name}"
    district_output = f"{assembly_path}/OUT_DISTRICT"
    gallery_output = f"{assembly_path}/OUT_GALLERY"
    camera_path = f"/obj/{camera_name}"

    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    manifest_dir = artifacts / "manifests"
    observation_dir = artifacts / "observations"
    scene_dir = artifacts / "scenes"
    geometry_dir = artifacts / "geometry"
    plan_manifest = manifest_dir / f"{run_id}_district_plan.json"
    result_manifest = manifest_dir / f"{run_id}_district_results.json"
    assembly_manifest = manifest_dir / f"{run_id}_district_assembly.json"
    validation_manifest = manifest_dir / f"{run_id}_district_validation.json"
    graph_manifest = manifest_dir / f"{run_id}_graph_manifest.json"
    scene_path = scene_dir / f"{run_id}_pdg_source.hipnc"
    source_svg = observation_dir / f"{run_id}_source_graph.svg"
    top_svg = observation_dir / f"{run_id}_top_graph.svg"
    assembly_svg = observation_dir / f"{run_id}_assembly_graph.svg"
    preview_path = observation_dir / f"{run_id}_district_preview.png"
    visual_manifest = manifest_dir / f"{run_id}_visual_verification.json"
    critique_packet = manifest_dir / f"{run_id}_critique_packet.json"

    seconds_per_item = 30.0
    worker_memory = 1_073_741_824
    max_points_per_item = 5_000
    max_primitives_per_item = 5_000
    max_output_bytes = lot_count * 10_000_000
    common = {
        "session_id": run_id,
        "project_id": SKILL_ID,
        "expected": {"skill": SKILL_ID, "skill_version": SKILL_VERSION, "run_id": run_id},
    }
    build_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=120,
        max_points=max_points_per_item,
        max_primitives=max_primitives_per_item,
        max_memory_bytes=worker_memory,
        max_work_items=lot_count,
        max_output_bytes=max_output_bytes,
    )
    pdg_policy = Policy(
        risk=RiskClass.MEDIUM,
        allow_external_process=True,
        max_seconds=lot_count * seconds_per_item,
        max_points=max_points_per_item,
        max_primitives=max_primitives_per_item,
        max_memory_bytes=worker_memory,
        max_work_items=lot_count,
        max_output_bytes=max_output_bytes,
    )
    assembly_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=90,
        max_points=150_000,
        max_primitives=100_000,
        max_memory_bytes=1_073_741_824,
        max_resolution=(1280, 720),
    )

    calls = [
        build_envelope(
            "district.build",
            {
                "output_dir": str(geometry_dir),
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_district_build.jsonl"),
                "source_name": source_name,
                "network_name": network_name,
                "base_seed": base_seed,
                "count": lot_count,
                "seed_step": seed_step,
                "columns": columns,
                "lot_spacing": float(lot_spacing),
                "scheduler_seconds_per_item": seconds_per_item,
                "scheduler_memory_mb": worker_memory // 1_048_576,
            },
            request_id=f"{run_id}-district-build",
            policy=build_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "district.generate",
            {"topnet_path": topnet_path, "output_path": str(plan_manifest)},
            request_id=f"{run_id}-district-generate",
            policy=build_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "district.cook",
            {
                "topnet_path": topnet_path,
                "manifest_path": str(plan_manifest),
                "result_path": str(result_manifest),
                "scene_path": str(scene_path),
                "log_path": str(log_dir / f"{run_id}_district_cook.jsonl"),
                "estimate": {
                    "work_items": lot_count,
                    "seconds_per_item": seconds_per_item,
                    "points_per_item": max_points_per_item,
                    "primitives_per_item": max_primitives_per_item,
                    "memory_bytes_per_item": worker_memory,
                    "output_bytes_total": max_output_bytes,
                },
            },
            request_id=f"{run_id}-district-cook",
            policy=pdg_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "district.assemble",
            {
                "result_path": str(result_manifest),
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_district_assembly.jsonl"),
                "manifest_path": str(assembly_manifest),
                "assembly_name": assembly_name,
                "camera_name": camera_name,
                "gallery_spacing": 6.0,
            },
            request_id=f"{run_id}-district-assemble",
            policy=build_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "district.validate",
            {
                "topnet_path": topnet_path,
                "assembly_path": assembly_path,
                "result_path": str(result_manifest),
                "assembly_manifest_path": str(assembly_manifest),
                "output_path": str(validation_manifest),
            },
            request_id=f"{run_id}-district-validate",
            policy=assembly_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_svg",
            {"node_path": source_path, "output_path": str(source_svg), "max_nodes": 32},
            request_id=f"{run_id}-source-svg",
            policy=assembly_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_svg",
            {"node_path": topnet_path, "output_path": str(top_svg), "max_nodes": 24},
            request_id=f"{run_id}-top-svg",
            policy=assembly_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_svg",
            {"node_path": assembly_path, "output_path": str(assembly_svg), "max_nodes": 128},
            request_id=f"{run_id}-assembly-svg",
            policy=assembly_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_manifest",
            {
                "node_path": assembly_path,
                "output_path": str(graph_manifest),
                "public_parameters": {},
                "metric_node_paths": [district_output, gallery_output],
                "metadata": {
                    "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
                    "recipes": [
                        {"id": "sop.procedural_building_lot", "version": "1.0.0"},
                        {"id": "top.procedural_district", "version": "1.0.0"},
                    ],
                    "source_result": str(result_manifest),
                    "assembly_manifest": str(assembly_manifest),
                    "selection": {
                        "method": "human",
                        "winner": None,
                        "automatic_ranking": False,
                    },
                    "scheduler": {"slots": 1, "background": False},
                    "preview": str(preview_path) if viewer_name else None,
                },
            },
            request_id=f"{run_id}-graph-manifest",
            policy=assembly_policy,
            **common,
        ).as_dict(),
    ]
    if viewer_name:
        calls.extend(
            [
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
                    request_id=f"{run_id}-district-preview",
                    policy=assembly_policy,
                    **common,
                ).as_dict(),
                build_envelope(
                    "visual.analyze",
                    {
                        "image_paths": [str(preview_path)],
                        "output_path": str(visual_manifest),
                        "panel_count": 1,
                    },
                    request_id=f"{run_id}-visual-analysis",
                    policy=assembly_policy,
                    **common,
                ).as_dict(),
                build_envelope(
                    "verification.critique.package",
                    {
                        "image_paths": [str(preview_path)],
                        "graph_path": str(assembly_svg),
                        "validation_paths": [
                            str(validation_manifest),
                            str(graph_manifest),
                            str(visual_manifest),
                        ],
                        "code_paths": [
                            str(Path(__file__).resolve()),
                            str(
                                Path(__file__).resolve().parents[2]
                                / "hermes_houdini"
                                / "district.py"
                            ),
                        ],
                        "output_path": str(critique_packet),
                    },
                    request_id=f"{run_id}-critique-packet",
                    policy=assembly_policy,
                    **common,
                ).as_dict(),
            ]
        )
    calls.append(
        build_envelope(
            "hip.save_snapshot",
            {"output_dir": str(scene_dir), "stem": f"{run_id}_final"},
            request_id=f"{run_id}-final-snapshot",
            policy=assembly_policy,
            **common,
        ).as_dict()
    )
    return calls


__all__ = ["SKILL_ID", "SKILL_VERSION", "plan"]
