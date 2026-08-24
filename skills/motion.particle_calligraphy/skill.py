"""Plan bounded native Particle Trail calligraphy and layered verification evidence."""

from __future__ import annotations

import re
from pathlib import Path

from hermes_houdini.calligraphy import (
    CALLIGRAPHY_ORDER,
    load_baked_audio_envelope,
    validate_calligraphy_spec,
)
from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "motion.particle_calligraphy"
SKILL_VERSION = "1.0.0"
RECIPE_ID = "sop.particle_calligraphy"
RECIPE_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,23}\Z")


def plan(
    parent_node_id: str,
    artifact_dir: str,
    run_id: str = "particle_calligraphy_001",
    seed: int = 5201,
    start_frame: int = 1,
    end_frame: int = 48,
    candidate_index: int = 0,
    birth_rate: float = 48.0,
    particle_life: float = 3.0,
    trail_frames: float = 12.0,
    trail_substeps: int = 8,
    wire_radius: float = 0.035,
    project_root: str = "",
    audio_envelope_relative_path: str = "",
    audio_modulation_depth: float = 0.5,
    viewer_name: str = "",
    viewport_name: str = "",
    camera_path: str = "",
) -> list[dict[str, object]]:
    """Return graph, optional baked modulation, temporal checks, evidence, and snapshot calls."""
    if not isinstance(parent_node_id, str) or not parent_node_id.startswith("/obj/"):
        raise ValueError("parent_node_id must be an absolute /obj SOP network path")
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-24 filename-safe characters")
    viewer_values = (viewer_name, viewport_name, camera_path)
    if any(viewer_values) and not all(viewer_values):
        raise ValueError("viewer_name, viewport_name, and camera_path must be provided together")
    spec = validate_calligraphy_spec(
        seed=seed,
        start_frame=start_frame,
        end_frame=end_frame,
        candidate_index=candidate_index,
        birth_rate=birth_rate,
        particle_life=particle_life,
        trail_frames=trail_frames,
        trail_substeps=trail_substeps,
        wire_radius=wire_radius,
    )
    if audio_envelope_relative_path:
        if not project_root:
            raise ValueError("project_root is required when audio_envelope_relative_path is set")
        load_baked_audio_envelope(
            project_root=project_root,
            relative_path=audio_envelope_relative_path,
            maximum_samples=spec["frame_count"],
        )
        if (
            not isinstance(audio_modulation_depth, (int, float))
            or isinstance(audio_modulation_depth, bool)
            or not 0 <= float(audio_modulation_depth) <= 1
        ):
            raise ValueError("audio_modulation_depth must be between 0 and 1")

    run_code = run_id.upper().replace("-", "_")
    base = parent_node_id.rstrip("/")
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    graph_log = log_dir / f"{run_id}_graph.jsonl"
    audio_log = log_dir / f"{run_id}_audio_envelope.jsonl"
    graph_svg = observation_dir / f"{run_id}_graph.svg"
    viewport_png = observation_dir / f"{run_id}_viewport.png"
    validation_path = manifest_dir / f"{run_id}_calligraphy_validation.json"
    graph_manifest = manifest_dir / f"{run_id}_graph_manifest.json"
    visual_report = manifest_dir / f"{run_id}_visual_verification.json"
    critique_packet = manifest_dir / f"{run_id}_critique_packet.json"
    particle_paths = [
        f"{base}/{run_code}_{candidate_id.upper()}_PARTICLES" for candidate_id in CALLIGRAPHY_ORDER
    ]
    trail_paths = [
        f"{base}/OUT_{run_code}_{candidate_id.upper()}_TRAIL" for candidate_id in CALLIGRAPHY_ORDER
    ]
    wire_paths = [
        f"{base}/OUT_{run_code}_{candidate_id.upper()}" for candidate_id in CALLIGRAPHY_ORDER
    ]
    selector_path = f"{base}/{run_code}_SELECT_CALLIGRAPHY"

    max_points = 100_000
    max_primitives = 100_000
    max_memory = 536_870_912
    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=45,
        max_points=max_points,
        max_primitives=max_primitives,
        max_memory_bytes=max_memory,
        max_frames=48,
    )
    cook_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=90,
        max_points=max_points,
        max_primitives=max_primitives,
        max_memory_bytes=max_memory,
        max_frames=48,
        max_resolution=(1280, 720),
    )
    common = {
        "session_id": run_id,
        "project_id": SKILL_ID,
        "expected": {"skill": SKILL_ID, "skill_version": SKILL_VERSION, "run_id": run_id},
    }
    recipe_inputs = {
        "run_code": run_code,
        "lineage": f"{SKILL_ID}@{SKILL_VERSION} run={run_id} seed={seed}",
        "seed_arc": spec["candidate_seeds"]["arc"],
        "seed_fan": spec["candidate_seeds"]["fan"],
        "seed_orbit": spec["candidate_seeds"]["orbit"],
        "birth_rate": spec["birth_rate"],
        "particle_life": spec["particle_life"],
        "trail_frames": spec["trail_frames"],
        "trail_substeps": spec["trail_substeps"],
        "wire_radius": spec["wire_radius"],
        "candidate_index": candidate_index,
    }
    metadata = {
        "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
        "recipe": {"id": RECIPE_ID, "version": RECIPE_VERSION},
        "run_id": run_id,
        "spec": spec,
        "candidates": [
            {
                "id": candidate_id,
                "seed": spec["candidate_seeds"][candidate_id],
                "lineage": f"{run_id}:{candidate_id}:seed={spec['candidate_seeds'][candidate_id]}",
                "human_rating": {"score": None, "notes": "", "selected": False},
                "automatic_rank": None,
            }
            for candidate_id in CALLIGRAPHY_ORDER
        ],
        "selection": {
            "method": "human",
            "preview_input": candidate_index,
            "winner": None,
            "automatic_ranking": False,
            "comparison_order": list(CALLIGRAPHY_ORDER),
        },
        "audio_envelope": {
            "mode": "baked_project_relative" if audio_envelope_relative_path else "silent_fixture",
            "relative_path": audio_envelope_relative_path or None,
            "modulation_depth": float(audio_modulation_depth)
            if audio_envelope_relative_path
            else 0.0,
        },
        "verification_ladder": [
            "temporal_graph_and_geometry_contracts",
            "deterministic_png_mechanical_checks_when_capture_exists",
            "optional_advisory_local_vlm_from_hashed_critique_packet",
            "optional_explicit_external_omnimodal_critique",
            "human_only_for_unresolved_taste_or_disagreement",
        ],
        "references": [
            "https://www.sidefx.com/docs/houdini/nodes/sop/particletrail.html",
            "https://www.sidefx.com/docs/houdini/dopparticles/attributes.html",
        ],
        "license": {
            "mode": "houdini-apprentice-noncommercial",
            "scene_extension": ".hipnc",
            "render_ceiling": [1280, 720],
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
                "checkpoint_stem": f"calligraphy_{run_id}",
            },
            request_id=f"{run_id}-graph",
            policy=graph_policy,
            **common,
        ).as_dict()
    ]
    if audio_envelope_relative_path:
        calls.append(
            build_envelope(
                "motion.calligraphy.apply_audio_envelope",
                {
                    "project_root": str(Path(project_root).expanduser().resolve()),
                    "relative_path": audio_envelope_relative_path,
                    "particle_paths": particle_paths,
                    "start_frame": start_frame,
                    "modulation_depth": float(audio_modulation_depth),
                    "checkpoint_dir": str(checkpoint_dir),
                    "log_path": str(audio_log),
                },
                request_id=f"{run_id}-audio-envelope",
                policy=graph_policy,
                **common,
            ).as_dict()
        )
    calls.extend(
        [
            build_envelope(
                "motion.calligraphy.validate",
                {
                    "network_path": parent_node_id,
                    "run_code": run_code,
                    "seed": seed,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "candidate_index": candidate_index,
                    "birth_rate": spec["birth_rate"],
                    "particle_life": spec["particle_life"],
                    "trail_frames": spec["trail_frames"],
                    "trail_substeps": spec["trail_substeps"],
                    "wire_radius": spec["wire_radius"],
                    "max_trail_points": max_points,
                    "audio_envelope_relative_path": audio_envelope_relative_path,
                    "output_path": str(validation_path),
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
                        **{
                            particle_paths[index]: [
                                "seed",
                                "birth",
                                "life",
                                "external",
                                "wind",
                                "turb",
                                "period",
                            ]
                            for index in range(3)
                        },
                        **{trail_paths[index]: ["integerframe", "frame"] for index in range(3)},
                        **{
                            wire_paths[index]: ["radius", "scaleattrib", "div"]
                            for index in range(3)
                        },
                        selector_path: ["input"],
                    },
                    "metric_node_paths": [],
                    "metadata": metadata,
                },
                request_id=f"{run_id}-manifest",
                policy=cook_policy,
                **common,
            ).as_dict(),
        ]
    )
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
                                / "calligraphy.py"
                            ),
                            str(
                                Path(__file__).resolve().parents[2]
                                / "recipes"
                                / "sop"
                                / "particle_calligraphy.yaml"
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
            {"output_dir": str(scene_dir), "stem": f"calligraphy_{run_id}_final"},
            request_id=f"{run_id}-snapshot",
            policy=cook_policy,
            **common,
        ).as_dict()
    )
    return calls


__all__ = ["plan"]
