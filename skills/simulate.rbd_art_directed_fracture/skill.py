"""Plan a bounded native art-directed RBD fracture study."""

from __future__ import annotations

import re
from pathlib import Path

from hermes_houdini.rbd import validate_rbd_spec
from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "simulate.rbd_art_directed_fracture"
SKILL_VERSION = "1.0.0"
RECIPE_ID = "sop.rbd_art_directed_fracture"
RECIPE_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,27}\Z")


def plan(
    parent_node_id: str,
    artifact_dir: str,
    run_id: str = "rbd_fracture_001",
    seed: int = 1717,
    start_frame: int = 1,
    end_frame: int = 48,
    profile_index: int = 0,
    bullet_substeps: int = 5,
    constraint_iterations: int = 10,
    primary_strength: float = 40.0,
    chipping_strength: float = 20.0,
    viewer_name: str = "",
    viewport_name: str = "",
    camera_path: str = "",
) -> list[dict[str, object]]:
    """Return checkpointed graph, temporal validation, evidence, and snapshot commands."""
    if not parent_node_id.startswith("/") or parent_node_id == "/":
        raise ValueError("parent_node_id must be an absolute SOP network path")
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-28 filename-safe characters")
    viewer_values = (viewer_name, viewport_name, camera_path)
    if any(viewer_values) and not all(viewer_values):
        raise ValueError("viewer_name, viewport_name, and camera_path must be provided together")
    spec = validate_rbd_spec(
        seed=seed,
        start_frame=start_frame,
        end_frame=end_frame,
        profile_index=profile_index,
        bullet_substeps=bullet_substeps,
        constraint_iterations=constraint_iterations,
        primary_strength=primary_strength,
        chipping_strength=chipping_strength,
    )

    run_code = run_id.upper().replace("-", "_")
    network = parent_node_id.rstrip("/")
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    graph_log = log_dir / f"{run_id}_graph.jsonl"
    graph_svg = observation_dir / f"{run_id}_graph.svg"
    graph_manifest = manifest_dir / f"{run_id}_graph_manifest.json"
    validation_path = manifest_dir / f"{run_id}_rbd_validation.json"
    viewport_png = observation_dir / f"{run_id}_frame_{end_frame}.png"
    visual_report = manifest_dir / f"{run_id}_visual_verification.json"
    critique_packet = manifest_dir / f"{run_id}_critique_packet.json"
    transform_cache = str(artifacts / "cache" / run_id / "v001" / "transforms.$F4.bgeo.sc")

    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=30,
        max_points=250_000,
        max_primitives=250_000,
        max_memory_bytes=1_073_741_824,
        max_frames=spec["frame_count"],
    )
    cook_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=120,
        max_points=250_000,
        max_primitives=250_000,
        max_memory_bytes=1_073_741_824,
        max_frames=spec["frame_count"],
        max_resolution=(1280, 720),
    )
    common = {
        "session_id": run_id,
        "project_id": SKILL_ID,
        "expected": {"skill": SKILL_ID, "skill_version": SKILL_VERSION, "run_id": run_id},
    }
    metadata = {
        "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
        "recipe": {"id": RECIPE_ID, "version": RECIPE_VERSION},
        "run_id": run_id,
        "source": {
            "material": "concrete",
            "operator": "Sop/rbdmaterialfracture::4.0",
            "tested_build": "22.0.368",
        },
        "profiles": [
            {
                "id": profile,
                "seed": spec["profile_seeds"][profile],
                "impact_points": spec["profile_point_counts"][profile],
                "human_rating": {"score": None, "notes": "", "selected": False},
                "automatic_rank": None,
            }
            for profile in spec["profile_order"]
        ],
        "temporal_contract": {
            "frames": [start_frame, end_frame, 1],
            "frame_count": spec["frame_count"],
            "stateful": True,
            "validator": str(validation_path),
        },
        "piece_budget": {"mode": "proxy", "maximum": 5_000},
        "transform_cache": {
            "representation": "Bullet Simulation Points",
            "attributes": ["name", "P", "orient", "pivot", "scale", "v", "w"],
            "path": transform_cache,
            "write_implicit": False,
            "status": "configured_not_written",
        },
        "selection": {
            "method": "human",
            "preview_input": profile_index,
            "winner": None,
            "automatic_ranking": False,
        },
        "license": {
            "mode": "houdini-apprentice-noncommercial",
            "commercial_use": False,
            "scene_extension": ".hipnc",
            "render_ceiling": [1280, 720],
        },
        "outputs": {
            "source": f"{network}/OUT_{run_code}_SOURCE",
            "rest_pieces": f"{network}/OUT_{run_code}_REST_PIECES",
            "constraints": f"{network}/OUT_{run_code}_CONSTRAINTS",
            "proxy": f"{network}/OUT_{run_code}_PROXY",
            "simulation": f"{network}/OUT_{run_code}_SIM_RAW",
            "transforms": f"{network}/OUT_{run_code}_TRANSFORMS",
            "after": f"{network}/OUT_{run_code}_AFTER",
            "comparison": f"{network}/OUT_{run_code}_COMPARE",
            "labels": f"{network}/OUT_{run_code}_LABELS",
        },
    }
    recipe_inputs = {
        "run_code": run_code,
        "lineage": f"{SKILL_ID}@{SKILL_VERSION} run={run_id}",
        "seed_radial": spec["profile_seeds"]["radial"],
        "seed_offset": spec["profile_seeds"]["offset"],
        "seed_layered": spec["profile_seeds"]["layered"],
        "profile_index": profile_index,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "bullet_substeps": bullet_substeps,
        "constraint_iterations": constraint_iterations,
        "primary_strength": primary_strength,
        "chipping_strength": chipping_strength,
        "transform_cache": transform_cache,
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
                "checkpoint_stem": f"rbd_{run_id}",
            },
            request_id=f"{run_id}-graph",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "simulate.rbd.validate",
            {
                "network_path": parent_node_id,
                "run_code": run_code,
                "seed": seed,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "profile_index": profile_index,
                "bullet_substeps": bullet_substeps,
                "constraint_iterations": constraint_iterations,
                "primary_strength": primary_strength,
                "chipping_strength": chipping_strength,
                "transform_cache_path": transform_cache,
                "output_path": str(validation_path),
                "max_pieces": 5_000,
            },
            request_id=f"{run_id}-validate",
            policy=cook_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_svg",
            {"node_path": parent_node_id, "output_path": str(graph_svg), "max_nodes": 64},
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
                    f"{network}/{run_code}_SELECT_IMPACT_PROFILE": ["input"],
                    f"{network}/{run_code}_MATERIAL_FRACTURE": [
                        "materialtype",
                        "concrete_fracturelevel",
                        "concrete_primarystrength",
                        "concrete_chippingstrength",
                    ],
                    f"{network}/{run_code}_BULLET_SOLVER": [
                        "startframe",
                        "substeps",
                        "numiteration",
                        "useground",
                        "cachemaxsize",
                    ],
                    f"{network}/{run_code}_TRANSFORM_FILE_CACHE": [
                        "file",
                        "f1",
                        "f2",
                        "loadfromdisk",
                    ],
                },
                "metric_node_paths": [
                    f"{network}/OUT_{run_code}_SOURCE",
                    f"{network}/OUT_{run_code}_REST_PIECES",
                    f"{network}/OUT_{run_code}_CONSTRAINTS",
                    f"{network}/OUT_{run_code}_PROXY",
                ],
                "metadata": metadata,
            },
            request_id=f"{run_id}-manifest",
            policy=cook_policy,
            **common,
        ).as_dict(),
    ]
    if all(viewer_values):
        calls.extend(
            [
                build_envelope(
                    "viewport.capture",
                    {
                        "viewer_name": viewer_name,
                        "viewport_name": viewport_name,
                        "camera_path": camera_path,
                        "output_path": str(viewport_png),
                        "frame": end_frame,
                        "width": 1280,
                        "height": 720,
                    },
                    request_id=f"{run_id}-viewport",
                    policy=cook_policy,
                    **common,
                ).as_dict(),
                build_envelope(
                    "visual.analyze",
                    {
                        "image_paths": [str(viewport_png)],
                        "output_path": str(visual_report),
                        "panel_count": 2,
                    },
                    request_id=f"{run_id}-visual-analysis",
                    policy=cook_policy,
                    **common,
                ).as_dict(),
                build_envelope(
                    "verification.critique.package",
                    {
                        "image_paths": [str(viewport_png)],
                        "graph_path": str(graph_svg),
                        "validation_paths": [
                            str(validation_path),
                            str(graph_manifest),
                            str(visual_report),
                        ],
                        "code_paths": [
                            str(Path(__file__).resolve()),
                            str(Path(__file__).resolve().parents[2] / "hermes_houdini" / "rbd.py"),
                            str(
                                Path(__file__).resolve().parents[2]
                                / "recipes"
                                / "sop"
                                / "rbd_art_directed_fracture.yaml"
                            ),
                        ],
                        "output_path": str(critique_packet),
                    },
                    request_id=f"{run_id}-critique-packet",
                    policy=cook_policy,
                    **common,
                ).as_dict(),
            ]
        )
    calls.append(
        build_envelope(
            "hip.save_snapshot",
            {"output_dir": str(scene_dir), "stem": f"rbd_{run_id}_final"},
            request_id=f"{run_id}-snapshot",
            policy=cook_policy,
            **common,
        ).as_dict()
    )
    return calls


__all__ = ["plan"]
