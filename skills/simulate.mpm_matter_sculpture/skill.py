"""Plan a bounded native multi-material MPM matter sculpture."""

from __future__ import annotations

import re
from pathlib import Path

from hermes_houdini.mpm import validate_mpm_spec
from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "simulate.mpm_matter_sculpture"
SKILL_VERSION = "1.0.0"
RECIPE_ID = "sop.mpm_matter_sculpture"
RECIPE_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,27}\Z")


def plan(
    parent_node_id: str,
    artifact_dir: str,
    run_id: str = "mpm_matter_001",
    seed: int = 1414,
    start_frame: int = 1,
    end_frame: int = 24,
    particle_separation: float = 0.12,
    source_radius: float = 0.62,
    source_height: float = 2.4,
    noise_height: float = 0.08,
    substep_min: int = 1,
    substep_max: int = 32,
    output_mode: str = "points",
    max_particles: int = 150_000,
    viewer_name: str = "",
    viewport_name: str = "",
    camera_path: str = "",
) -> list[dict[str, object]]:
    """Return checkpointed build, proxy validation, evidence, and snapshot calls."""
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
    spec = validate_mpm_spec(
        seed=seed,
        start_frame=start_frame,
        end_frame=end_frame,
        particle_separation=particle_separation,
        source_radius=source_radius,
        source_height=source_height,
        noise_height=noise_height,
        substep_min=substep_min,
        substep_max=substep_max,
        output_mode=output_mode,
        max_particles=max_particles,
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
    validation_path = manifest_dir / f"{run_id}_mpm_validation.json"
    progress_path = manifest_dir / f"{run_id}_cache_progress.json"
    viewport_png = observation_dir / f"{run_id}_frame_{end_frame}.png"
    visual_report = manifest_dir / f"{run_id}_visual_verification.json"
    critique_packet = manifest_dir / f"{run_id}_critique_packet.json"
    cache_path = artifacts / "cache" / run_id / "v001" / f"{run_id}.$F4.bgeo.sc"
    network = parent_node_id.rstrip("/")
    source_paths = {
        profile: f"{network}/{run_code}_{profile.upper()}_SOURCE"
        for profile in spec["profile_order"]
    }
    container_path = f"{network}/{run_code}_MPM_CONTAINER"
    solver_path = f"{network}/{run_code}_MPM_SOLVER"
    selector_path = f"{network}/{run_code}_SELECT_OUTPUT"

    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=30,
        max_points=max_particles,
        max_primitives=max_particles,
        max_memory_bytes=1_073_741_824,
        max_frames=spec["frame_count"],
    )
    cook_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=180,
        max_points=max_particles,
        max_primitives=max_particles,
        max_memory_bytes=1_073_741_824,
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
        "seed_granular": spec["profile_seeds"]["granular"],
        "seed_elastic": spec["profile_seeds"]["elastic"],
        "seed_viscous": spec["profile_seeds"]["viscous"],
        "start_frame": start_frame,
        "end_frame": end_frame,
        "particle_separation": particle_separation,
        "source_radius": source_radius,
        "source_height": source_height,
        "noise_height": noise_height,
        "substep_min": substep_min,
        "substep_max": substep_max,
        "cache_path": str(cache_path),
        "output_index": spec["output_index"],
    }
    metadata = {
        "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
        "recipe": {"id": RECIPE_ID, "version": RECIPE_VERSION},
        "run_id": run_id,
        "profile_order": spec["profile_order"],
        "profile_seeds": spec["profile_seeds"],
        "material_profiles": spec["material_profiles"],
        "preset_contract": {
            "mode": "explicit_coefficients",
            "reason": "Houdini material preset menu is callback-driven",
            "physical_identity_claimed": False,
        },
        "resource_contract": {
            "proxy_first": True,
            "estimated_particles": spec["estimated_particles"],
            "max_particles": max_particles,
            "roadmap_ceiling_requires_separate_approval": 1_000_000,
        },
        "temporal_contract": {
            "frames": [start_frame, end_frame, 1],
            "frame_count": spec["frame_count"],
            "stateful": True,
            "validator": str(validation_path),
        },
        "cache_contract": {
            "path": str(cache_path),
            "format": ".bgeo.sc",
            "file_mode": "none",
            "write_implicit": False,
            "status": "configured_not_written",
            "progress_manifest": str(progress_path),
        },
        "selection": {
            "method": "human",
            "output_mode": output_mode,
            "winner": None,
            "automatic_ranking": False,
            "human_ratings": {
                profile: {"score": None, "notes": "", "selected": False}
                for profile in spec["profile_order"]
            },
        },
        "license": {
            "mode": "houdini-apprentice-noncommercial",
            "commercial_use": False,
            "scene_extension": ".hipnc",
            "render_ceiling": [1280, 720],
        },
        "outputs": {
            "sources": source_paths,
            "container": container_path,
            "collider": f"{network}/OUT_{run_code}_COLLIDER",
            "points": f"{network}/OUT_{run_code}_POINTS",
            "surface": f"{network}/OUT_{run_code}_SURFACE",
            "selected": f"{network}/OUT_{run_code}_SELECTED",
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
                "checkpoint_stem": f"mpm_{run_id}",
            },
            request_id=f"{run_id}-graph",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "simulate.mpm.validate",
            {
                "network_path": parent_node_id,
                "run_code": run_code,
                "seed": seed,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "particle_separation": particle_separation,
                "source_radius": source_radius,
                "source_height": source_height,
                "noise_height": noise_height,
                "substep_min": substep_min,
                "substep_max": substep_max,
                "output_mode": output_mode,
                "cache_path": str(cache_path),
                "progress_path": str(progress_path),
                "output_path": str(validation_path),
                "max_particles": max_particles,
            },
            request_id=f"{run_id}-validate",
            policy=cook_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_svg",
            {"node_path": parent_node_id, "output_path": str(graph_svg), "max_nodes": 48},
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
                    container_path: ["particlesep", "gridscale", "size", "allbounds"],
                    source_paths["granular"]: [
                        "materialtype",
                        "density",
                        "e",
                        "eexp",
                        "sandfrictionangle",
                        "sandcohesion",
                    ],
                    source_paths["elastic"]: ["materialtype", "density", "e", "eexp", "nu"],
                    source_paths["viscous"]: [
                        "materialtype",
                        "density",
                        "k",
                        "kexp",
                        "gamma",
                        "viscosity",
                        "viscokappa",
                    ],
                    solver_path: [
                        "substeprange",
                        "gravity",
                        "groundactive",
                        "cachemaxsize",
                        "deterministic",
                        "savecheckpoints",
                    ],
                    selector_path: ["input"],
                },
                # Stateful MPM nodes become dirty when the validator restores the artist's
                # original frame. Their verified metrics live in validation_path; the graph
                # manifest remains deliberately cook-free.
                "metric_node_paths": [],
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
                        "panel_count": 1,
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
                            str(Path(__file__).resolve().parents[2] / "hermes_houdini" / "mpm.py"),
                            str(
                                Path(__file__).resolve().parents[2]
                                / "recipes"
                                / "sop"
                                / "mpm_matter_sculpture.yaml"
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
            {"output_dir": str(scene_dir), "stem": f"mpm_{run_id}_final"},
            request_id=f"{run_id}-snapshot",
            policy=cook_policy,
            **common,
        ).as_dict()
    )
    return calls


__all__ = ["plan"]
