"""Plan one bounded, editable native L-System botanical grammar gallery."""

from __future__ import annotations

import re
from pathlib import Path

from hermes_houdini.botanical import BOTANICAL_GRAMMARS, BOTANICAL_ORDER, validate_botanical_spec
from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "grow.botanical_grammar"
SKILL_VERSION = "1.0.0"
RECIPE_ID = "sop.lsystem_botanical"
RECIPE_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,27}\Z")


def plan(
    parent_node_id: str,
    artifact_dir: str,
    run_id: str = "botanical_grammar_001",
    seed: int = 4103,
    generations: int = 6,
    candidate_index: int = 0,
    wire_radius: float = 0.018,
    viewer_name: str = "",
    viewport_name: str = "",
    camera_path: str = "",
) -> list[dict[str, object]]:
    """Return graph, bounded validation, observation, optional viewport, and snapshot calls."""
    if not isinstance(parent_node_id, str) or not parent_node_id.startswith("/obj/"):
        raise ValueError("parent_node_id must be an absolute /obj SOP network path")
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-28 filename-safe characters")
    viewer_values = (viewer_name, viewport_name, camera_path)
    if any(viewer_values) and not all(viewer_values):
        raise ValueError("viewer_name, viewport_name, and camera_path must be provided together")
    spec = validate_botanical_spec(
        generations=generations,
        seed=seed,
        candidate_index=candidate_index,
        wire_radius=wire_radius,
    )

    run_code = run_id.upper().replace("-", "_")
    base = parent_node_id.rstrip("/")
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    graph_log = log_dir / f"{run_id}_graph.jsonl"
    graph_svg = observation_dir / f"{run_id}_graph.svg"
    preview_path = observation_dir / f"{run_id}_viewport.png"
    validation_path = manifest_dir / f"{run_id}_botanical_validation.json"
    graph_manifest = manifest_dir / f"{run_id}_graph_manifest.json"

    skeleton_paths = [
        f"{base}/{run_code}_{grammar_id.upper()}_SKELETON" for grammar_id in BOTANICAL_ORDER
    ]
    wire_paths = [f"{base}/OUT_{run_code}_{grammar_id.upper()}" for grammar_id in BOTANICAL_ORDER]
    polywire_paths = [
        f"{base}/{run_code}_{grammar_id.upper()}_POLYWIRE" for grammar_id in BOTANICAL_ORDER
    ]
    selector_path = f"{base}/{run_code}_SELECT_BOTANICAL"
    selected_path = f"{base}/OUT_{run_code}_SELECTED"
    compare_path = f"{base}/OUT_{run_code}_COMPARE"

    max_points = 250_000
    max_primitives = 250_000
    max_memory = 536_870_912
    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=30,
        max_points=max_points,
        max_primitives=max_primitives,
        max_memory_bytes=max_memory,
        max_frames=1,
    )
    cook_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=90,
        max_points=max_points,
        max_primitives=max_primitives,
        max_memory_bytes=max_memory,
        max_frames=1,
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
        "generations": generations,
        "seed_canopy": spec["candidate_seeds"]["canopy"],
        "seed_fern": spec["candidate_seeds"]["fern"],
        "seed_coral": spec["candidate_seeds"]["coral"],
        "candidate_index": candidate_index,
        "wire_radius": spec["wire_radius"],
    }
    candidates = [
        {
            "id": grammar_id,
            "seed": spec["candidate_seeds"][grammar_id],
            "premise": BOTANICAL_GRAMMARS[grammar_id]["premise"],
            "rules": list(BOTANICAL_GRAMMARS[grammar_id]["rules"]),
            "lineage": f"{run_id}:{grammar_id}:seed={spec['candidate_seeds'][grammar_id]}",
            "human_rating": {"score": None, "notes": "", "selected": False},
            "automatic_rank": None,
        }
        for grammar_id in BOTANICAL_ORDER
    ]
    metadata = {
        "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
        "recipe": {"id": RECIPE_ID, "version": RECIPE_VERSION},
        "run_id": run_id,
        "seed": seed,
        "candidates": candidates,
        "selection": {
            "method": "human",
            "preview_input": candidate_index,
            "winner": None,
            "automatic_ranking": False,
            "comparison_order": list(BOTANICAL_ORDER),
        },
        "algorithm": {
            "context": "SOP",
            "native_nodes": ["lsystem", "polywire", "xform", "switch", "merge", "null"],
            "safe_registered_grammars_only": True,
            "rule_file_io": False,
            "python_geometry_compute": False,
        },
        "resource_contract": {
            "generations": generations,
            "max_generations": 6,
            "max_points": max_points,
            "max_primitives": max_primitives,
            "estimated_wire_points": spec["estimated_wire_points"],
            "estimated_wire_primitives": spec["estimated_wire_primitives"],
            "max_seconds": 90,
        },
        "outputs": {
            "skeletons": dict(zip(BOTANICAL_ORDER, skeleton_paths, strict=True)),
            "wires": dict(zip(BOTANICAL_ORDER, wire_paths, strict=True)),
            "selected": selected_path,
            "comparison": compare_path,
        },
        "evidence": {
            "geometry_validation": str(validation_path),
            "graph_svg": str(graph_svg),
            "viewport": str(preview_path) if all(viewer_values) else None,
        },
        "references": [
            "https://www.sidefx.com/docs/houdini/nodes/sop/lsystem",
            "https://www.sidefx.com/tutorials/l-systems-node/?collection=63",
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
                "checkpoint_stem": f"botanical_{run_id}",
            },
            request_id=f"{run_id}-graph",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "botanical.validate",
            {
                "network_path": parent_node_id,
                "skeleton_node_paths": skeleton_paths,
                "wire_node_paths": wire_paths,
                "selected_path": selected_path,
                "compare_path": compare_path,
                "generations": generations,
                "seed": seed,
                "candidate_index": candidate_index,
                "wire_radius": spec["wire_radius"],
                "output_path": str(validation_path),
            },
            request_id=f"{run_id}-validate",
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
                    skeleton_paths[0]: [
                        "generations",
                        "randscale",
                        "randseed",
                        "stepinit",
                        "stepscale",
                        "angleinit",
                        "premise",
                        "rule1",
                    ],
                    skeleton_paths[1]: [
                        "generations",
                        "randscale",
                        "randseed",
                        "stepinit",
                        "stepscale",
                        "angleinit",
                        "premise",
                        "rule1",
                        "rule2",
                    ],
                    skeleton_paths[2]: [
                        "generations",
                        "randscale",
                        "randseed",
                        "stepinit",
                        "stepscale",
                        "angleinit",
                        "premise",
                        "rule1",
                    ],
                    polywire_paths[0]: ["radius", "scaleattrib", "div"],
                    polywire_paths[1]: ["radius", "scaleattrib", "div"],
                    polywire_paths[2]: ["radius", "scaleattrib", "div"],
                    selector_path: ["input"],
                },
                "metric_node_paths": [*skeleton_paths, *wire_paths, selected_path, compare_path],
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
                    "frame": 1.0,
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
            {"output_dir": str(scene_dir), "stem": f"botanical_{run_id}_final"},
            request_id=f"{run_id}-snapshot",
            policy=cook_policy,
            **common,
        ).as_dict()
    )
    return calls


__all__ = ["plan"]
