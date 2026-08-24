"""Plan a bounded three-material native Vellum membrane study."""

from __future__ import annotations

import re
from pathlib import Path

from hermes_houdini.membrane import validate_membrane_spec
from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "simulate.vellum_membrane_lab"
SKILL_VERSION = "1.0.0"
RECIPE_ID = "sop.vellum_membrane_lab"
RECIPE_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,27}\Z")


def plan(
    parent_node_id: str,
    artifact_dir: str,
    run_id: str = "vellum_membrane_001",
    seed: int = 1313,
    start_frame: int = 1,
    end_frame: int = 24,
    candidate_index: int = 0,
    resolution: int = 25,
    sheet_size: float = 2.4,
    sheet_height: float = 2.5,
    noise_height: float = 0.035,
    mass: float = 0.08,
    thickness: float = 0.025,
    substeps: int = 2,
    constraint_iterations: int = 60,
    viewer_name: str = "",
    viewport_name: str = "",
    camera_path: str = "",
) -> list[dict[str, object]]:
    """Return checkpointed build, exact temporal verification, evidence, and snapshot calls."""
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
    spec = validate_membrane_spec(
        seed=seed,
        start_frame=start_frame,
        end_frame=end_frame,
        candidate_index=candidate_index,
        resolution=resolution,
        sheet_size=sheet_size,
        sheet_height=sheet_height,
        noise_height=noise_height,
        mass=mass,
        thickness=thickness,
        substeps=substeps,
        constraint_iterations=constraint_iterations,
    )

    run_code = run_id.upper().replace("-", "_")
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    graph_log = log_dir / f"{run_id}_graph.jsonl"
    graph_svg = observation_dir / f"{run_id}_graph.svg"
    graph_manifest = manifest_dir / f"{run_id}_graph_manifest.json"
    validation_path = manifest_dir / f"{run_id}_membrane_validation.json"
    viewport_png = observation_dir / f"{run_id}_frame_{end_frame}.png"
    visual_report = manifest_dir / f"{run_id}_visual_verification.json"
    critique_packet = manifest_dir / f"{run_id}_critique_packet.json"
    cache_paths = {
        candidate: str(artifacts / "cache" / run_id / "v001" / f"{candidate}.$F4.bgeo.sc")
        for candidate in spec["candidate_order"]
    }
    network = parent_node_id.rstrip("/")
    outputs = {
        candidate: f"{network}/OUT_{run_code}_{candidate.upper()}"
        for candidate in spec["candidate_order"]
    }
    compare_path = f"{network}/OUT_{run_code}_COMPARE"
    rest_outputs = {
        candidate: f"{network}/OUT_{run_code}_{candidate.upper()}_REST"
        for candidate in spec["candidate_order"]
    }
    collider_path = f"{network}/OUT_{run_code}_COLLIDER"
    selector_path = f"{network}/{run_code}_SELECT_MEMBRANE"

    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=30,
        max_points=75_000,
        max_primitives=75_000,
        max_memory_bytes=536_870_912,
        max_frames=spec["frame_count"],
    )
    cook_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=90,
        max_points=75_000,
        max_primitives=75_000,
        max_memory_bytes=536_870_912,
        max_frames=spec["frame_count"],
        max_resolution=(1280, 720),
    )
    common = {
        "session_id": run_id,
        "project_id": SKILL_ID,
        "expected": {"skill": SKILL_ID, "skill_version": SKILL_VERSION, "run_id": run_id},
    }
    recipe_inputs = {
        "run_code": run_code,
        "lineage": f"{SKILL_ID}@{SKILL_VERSION} run={run_id}",
        "resolution": resolution,
        "sheet_size": sheet_size,
        "sheet_height": sheet_height,
        "anchor_z": sheet_size / 2.0,
        "noise_height": noise_height,
        "seed_silk": spec["candidate_seeds"]["silk"],
        "seed_rubber": spec["candidate_seeds"]["rubber"],
        "seed_reinforced": spec["candidate_seeds"]["reinforced"],
        "mass": mass,
        "thickness": thickness,
        "substeps": substeps,
        "constraint_iterations": constraint_iterations,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "cache_silk": cache_paths["silk"],
        "cache_rubber": cache_paths["rubber"],
        "cache_reinforced": cache_paths["reinforced"],
        "candidate_index": candidate_index,
    }
    metadata = {
        "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
        "recipe": {"id": RECIPE_ID, "version": RECIPE_VERSION},
        "run_id": run_id,
        "candidate_order": spec["candidate_order"],
        "candidate_seeds": spec["candidate_seeds"],
        "material_profiles": spec["material_profiles"],
        "temporal_contract": {
            "frames": [start_frame, end_frame, 1],
            "frame_count": spec["frame_count"],
            "stateful": True,
            "validator": str(validation_path),
        },
        "cache_contract": {
            "paths": cache_paths,
            "format": ".bgeo.sc",
            "write_implicit": False,
            "status": "configured_not_written",
        },
        "selection": {
            "method": "human",
            "preview_input": candidate_index,
            "winner": None,
            "automatic_ranking": False,
            "human_ratings": {
                candidate: {"score": None, "notes": "", "selected": False}
                for candidate in spec["candidate_order"]
            },
        },
        "license": {
            "mode": "houdini-apprentice-noncommercial",
            "commercial_use": False,
            "scene_extension": ".hipnc",
            "render_ceiling": [1280, 720],
        },
        "outputs": {
            "candidates": outputs,
            "selected": f"{network}/OUT_{run_code}_SELECTED",
            "comparison": compare_path,
            "labels": f"{network}/OUT_{run_code}_LABELS",
        },
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
                "checkpoint_stem": f"membrane_{run_id}",
            },
            request_id=f"{run_id}-graph",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "simulate.membrane.validate",
            {
                "network_path": parent_node_id,
                "run_code": run_code,
                "seed": seed,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "candidate_index": candidate_index,
                "resolution": resolution,
                "sheet_size": sheet_size,
                "sheet_height": sheet_height,
                "noise_height": noise_height,
                "mass": mass,
                "thickness": thickness,
                "substeps": substeps,
                "constraint_iterations": constraint_iterations,
                "cache_paths": cache_paths,
                "output_path": str(validation_path),
                "max_points": 75_000,
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
                    selector_path: ["input"],
                    f"{network}/{run_code}_SILK_CLOTH": [
                        "stretchstiffness",
                        "stretchstiffnessexp",
                        "bendstiffness",
                        "bendstiffnessexp",
                    ],
                    f"{network}/{run_code}_RUBBER_CLOTH": [
                        "stretchstiffness",
                        "stretchstiffnessexp",
                        "bendstiffness",
                        "bendstiffnessexp",
                    ],
                    f"{network}/{run_code}_REINFORCED_SURFACE_STRUTS": [
                        "constrainttype",
                        "strut_maxlen",
                        "strut_constraintsperpt",
                        "strut_seed",
                    ],
                    f"{network}/{run_code}_SILK_SOLVER": [
                        "substeps",
                        "niter",
                        "smoothiter",
                        "gravityy",
                        "windx",
                        "windz",
                        "windspeed",
                        "winddrag",
                    ],
                },
                "metric_node_paths": [*rest_outputs.values(), collider_path],
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
                        "panel_count": 3,
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
                            str(
                                Path(__file__).resolve().parents[2]
                                / "hermes_houdini"
                                / "membrane.py"
                            ),
                            str(
                                Path(__file__).resolve().parents[2]
                                / "recipes"
                                / "sop"
                                / "vellum_membrane_lab.yaml"
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
            {"output_dir": str(scene_dir), "stem": f"membrane_{run_id}_final"},
            request_id=f"{run_id}-snapshot",
            policy=cook_policy,
            **common,
        ).as_dict()
    )
    return calls


__all__ = ["plan"]
