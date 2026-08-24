"""Plan one bounded, editable native-SOP differential-growth run."""

from __future__ import annotations

import math
import re
from pathlib import Path

from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "generate.differential_growth"
SKILL_VERSION = "1.0.0"
RECIPE_ID = "sop.differential_growth_loop"
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


def _seed_offsets(seed: int) -> tuple[float, float, float]:
    return (
        round((seed % 997) / 37.0, 8),
        round(((seed * 17 + 23) % 991) / 41.0, 8),
        round(((seed * 31 + 7) % 983) / 43.0, 8),
    )


def plan(
    parent_node_id: str,
    artifact_dir: str,
    run_id: str = "differential_growth_001",
    seed: int = 2401,
    candidate_index: int = 1,
    start_frame: float = 1.0,
    end_frame: float = 24.0,
    frame_step: float = 1.0,
    point_radius: float = 0.075,
    relax_iterations: int = 5,
    blur_iterations: int = 1,
    blur_step_size: float = 0.25,
    segment_length: float = 0.075,
    source_jitter: float = 0.025,
    wire_radius: float = 0.025,
    viewer_name: str = "",
    viewport_name: str = "",
    camera_path: str = "",
) -> list[dict[str, object]]:
    """Return checkpointed graph, solver population, cook, evidence, and snapshot calls."""
    if not parent_node_id.startswith("/") or parent_node_id == "/":
        raise ValueError("parent_node_id must be an absolute SOP network path")
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-28 filename-safe characters")
    frames = _frame_count(start_frame, end_frame, frame_step)
    if frames > 24:
        raise ValueError("this skill is bounded to at most 24 frames")
    viewer_values = (viewer_name, viewport_name, camera_path)
    if any(viewer_values) and not all(viewer_values):
        raise ValueError("viewer_name, viewport_name, and camera_path must be provided together")

    run_code = run_id.upper().replace("-", "_")
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    graph_log = log_dir / f"{run_id}_graph.jsonl"
    solver_log = log_dir / f"{run_id}_solver.jsonl"
    cook_log = log_dir / f"{run_id}_temporal_cook.jsonl"
    graph_svg = observation_dir / f"{run_id}_graph.svg"
    solver_svg = observation_dir / f"{run_id}_solver_graph.svg"
    graph_manifest = manifest_dir / f"{run_id}_graph_manifest.json"
    preview_path = observation_dir / f"{run_id}_frame_{end_frame:g}.png"

    base = parent_node_id.rstrip("/")
    selector_path = f"{base}/{run_code}_SELECT_SOURCE"
    noise_path = f"{base}/{run_code}_SEEDED_PERTURB"
    initial_spacing_path = f"{base}/{run_code}_INITIAL_EDGE_SPACING"
    solver_path = f"{base}/{run_code}_SOLVER"
    feedback_path = f"{solver_path}/d/s"
    separation_path = f"{feedback_path}/HERMES_POINT_SEPARATION"
    smoothing_path = f"{feedback_path}/HERMES_CURVE_RELAX"
    spacing_path = f"{feedback_path}/HERMES_EDGE_SPACING"
    rest_path = f"{base}/OUT_{run_code}_REST_CURVE"
    curve_path = f"{base}/OUT_{run_code}_GROWTH_CURVE"
    wire_path = f"{base}/OUT_{run_code}_GROWTH_WIRE"
    compare_path = f"{base}/OUT_{run_code}_COMPARE"
    noise_offsets = _seed_offsets(seed)

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
        "lineage": f"{SKILL_ID}@{SKILL_VERSION} run={run_id} seed={seed}",
        "candidate_index": candidate_index,
        "source_jitter": source_jitter,
        "noise_offset_x": noise_offsets[0],
        "noise_offset_y": noise_offsets[1],
        "noise_offset_z": noise_offsets[2],
        "initial_segment_length": min(0.25, max(0.02, segment_length / 0.75)),
        "start_frame": start_frame,
        "wire_radius": wire_radius,
    }
    candidates = [
        {"id": "circle", "source_type": "circle", "closed": True},
        {"id": "ellipse", "source_type": "circle", "closed": True},
        {"id": "spiral", "source_type": "spiral", "closed": False},
    ]
    metadata = {
        "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
        "recipe": {"id": RECIPE_ID, "version": RECIPE_VERSION},
        "run_id": run_id,
        "seed": seed,
        "candidates": [
            {
                **candidate,
                "seed": seed,
                "lineage": f"{run_id}:{candidate['id']}:seed={seed}",
                "human_rating": {"score": None, "notes": "", "selected": False},
                "automatic_rank": None,
            }
            for candidate in candidates
        ],
        "selection": {
            "method": "human",
            "preview_input": candidate_index,
            "winner": None,
            "automatic_ranking": False,
        },
        "algorithm": {
            "context": "SOP",
            "solver_type": "solver",
            "feedback_nodes": ["relax", "attribblur", "resample"],
            "parameters": {
                "point_radius": point_radius,
                "relax_iterations": relax_iterations,
                "blur_iterations": blur_iterations,
                "blur_step_size": blur_step_size,
                "segment_length": segment_length,
            },
            "python_geometry_compute": False,
        },
        "temporal_contract": {
            "frames": [start_frame, end_frame, frame_step],
            "frame_count": frames,
            "cook_log": str(cook_log),
            "stateful": True,
            "memory_cache_only": True,
        },
        "outputs": {"rest_curve": rest_path, "grown_curve": curve_path, "wire": wire_path},
        "references": [
            "https://www.sidefx.com/tutorials/complex-growth-in-2-nodes/",
            "https://www.sidefx.com/docs/houdini/nodes/sop/attribblur.html",
            "https://www.sidefx.com/docs/houdini/nodes/sop/resample.html",
            "https://www.sidefx.com/docs/houdini/nodes/sop/polywire.html",
        ],
        "license": {
            "mode": "houdini-apprentice-noncommercial",
            "commercial_use": False,
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
                "checkpoint_stem": f"growth_{run_id}",
            },
            request_id=f"{run_id}-graph",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "growth.solver.populate",
            {
                "solver_path": solver_path,
                "run_id": run_id,
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(solver_log),
                "point_radius": point_radius,
                "relax_iterations": relax_iterations,
                "blur_iterations": blur_iterations,
                "blur_step_size": blur_step_size,
                "segment_length": segment_length,
            },
            request_id=f"{run_id}-solver",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "cook.node",
            {
                "node_path": compare_path,
                "scope": "frame_range",
                "frame": None,
                "frame_range": [start_frame, end_frame, frame_step],
                "force": True,
                "estimate": {
                    "points": max_points,
                    "primitives": max_primitives,
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
                    "min_points": 16,
                    "max_points": 1000,
                    "min_primitives": 1,
                    "max_primitives": 4,
                    "require_finite_bounds": True,
                    "allow_warnings": False,
                },
            },
            request_id=f"{run_id}-rest-validate",
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
            "graph.capture_svg",
            {"node_path": feedback_path, "output_path": str(solver_svg), "max_nodes": 16},
            request_id=f"{run_id}-solver-svg",
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
                    noise_path: ["height", "elementsize", "offsetx", "offsety", "offsetz"],
                    initial_spacing_path: ["length"],
                    solver_path: [
                        "startframe",
                        "substep",
                        "cacheenabled",
                        "cachetodisk",
                        "cachemaxsize",
                    ],
                    separation_path: ["radius", "maxiterations", "useradiusattrib"],
                    smoothing_path: [
                        "attributes",
                        "method",
                        "influencetype",
                        "iterations",
                        "stepsize",
                    ],
                    spacing_path: ["length", "dolength", "useattribs"],
                    wire_path: ["radius", "div"],
                },
                "metric_node_paths": [rest_path],
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
            {"output_dir": str(scene_dir), "stem": f"growth_{run_id}_final"},
            request_id=f"{run_id}-snapshot",
            policy=cook_policy,
            **common,
        ).as_dict()
    )
    return calls


__all__ = ["plan"]
