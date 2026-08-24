"""Plan one bounded three-candidate native Copernicus Reaction-Diffusion run."""

from __future__ import annotations

import re
from pathlib import Path

from hermes_houdini.copernicus import REACTION_PRESETS, validate_reaction_spec
from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "generate.reaction_diffusion_pattern"
SKILL_VERSION = "1.0.0"
RECIPE_ID = "cop.reaction_diffusion_pattern"
RECIPE_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,23}\Z")


def _seed_offsets(seed: int) -> tuple[float, float]:
    return (
        round((seed % 997) / 31.0, 8),
        round(((seed * 29 + 17) % 991) / 37.0, 8),
    )


def plan(
    artifact_dir: str,
    run_id: str = "reaction_diffusion_001",
    network_parent_path: str = "/img",
    seed: int = 3109,
    resolution: int = 256,
    candidate_index: int = 0,
    iterations: int = 8,
    iterations_per_step: int = 6,
    activation_threshold: float = 0.62,
    activation_width: float = 0.03,
    noise_element_size: float = 0.12,
) -> list[dict[str, object]]:
    """Return network, recipe, bounded cook, image export, evidence, and snapshot calls."""
    if network_parent_path != "/img":
        raise ValueError("Sprint 10 is intentionally bounded to the explicit /img manager")
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-24 filename-safe characters")
    spec = validate_reaction_spec(
        resolution=resolution,
        iterations=iterations,
        iterations_per_step=iterations_per_step,
        candidate_index=candidate_index,
    )

    run_code = run_id.upper().replace("-", "_")
    network_name = f"{run_code}_COPNET"
    network_path = f"/img/{network_name}"
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    network_log = log_dir / f"{run_id}_network.jsonl"
    graph_log = log_dir / f"{run_id}_graph.jsonl"
    contact_export_log = log_dir / f"{run_id}_contact_export.jsonl"
    selected_export_log = log_dir / f"{run_id}_selected_export.jsonl"
    validation_path = manifest_dir / f"{run_id}_image_validation.json"
    graph_manifest = manifest_dir / f"{run_id}_graph_manifest.json"
    graph_svg = observation_dir / f"{run_id}_graph.svg"
    contact_output = observation_dir / f"{run_id}_contact_sheet.png"
    selected_output = observation_dir / f"{run_id}_selected.png"

    noise_path = f"{network_path}/{run_code}_ACTIVATION_NOISE"
    threshold_path = f"{network_path}/{run_code}_ACTIVATION_THRESHOLD"
    end_paths = [
        f"{network_path}/{run_code}_SMALL_WAVES",
        f"{network_path}/{run_code}_LARGE_WAVES",
        f"{network_path}/{run_code}_SPOTS",
    ]
    selector_path = f"{network_path}/{run_code}_SELECT_PATTERN"
    contact_sheet_path = f"{network_path}/OUT_{run_code}_CONTACT_SHEET"
    selected_path = f"{network_path}/OUT_{run_code}_SELECTED"
    contact_rop_path = f"{network_path}/{run_code}_EXPORT_CONTACT_SHEET"
    selected_rop_path = f"{network_path}/{run_code}_EXPORT_SELECTED"
    noise_offsets = _seed_offsets(seed)

    contact_width, contact_height = spec["contact_resolution"]
    max_width = max(resolution, contact_width)
    max_height = max(resolution, contact_height)
    max_memory = 536_870_912
    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=30,
        max_memory_bytes=max_memory,
        max_resolution=(max_width, max_height),
    )
    cook_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=90,
        max_memory_bytes=max_memory,
        max_resolution=(max_width, max_height),
    )
    export_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=90,
        max_frames=1,
        max_memory_bytes=max_memory,
        max_output_bytes=104_857_600,
        max_resolution=(max_width, max_height),
    )
    common = {
        "session_id": run_id,
        "project_id": SKILL_ID,
        "expected": {"skill": SKILL_ID, "skill_version": SKILL_VERSION, "run_id": run_id},
    }
    network_operations = [
        {
            "op": "create",
            "ref": "copnet",
            "parent_path": network_parent_path,
            "operator_type": "copnet",
            "name": network_name,
            "exact_name": True,
            "category": "CopNet",
            "role": "reaction_diffusion_network",
            "position": [0.0, 0.0],
            "parameters": {
                "setres": 1,
                "res": [resolution, resolution],
                "setpixelscale": 1,
                "pixelscale": 1.0,
                "setprecision": 1,
                "precision": 1,
            },
            "comment": (
                f"{SKILL_ID}@{SKILL_VERSION} run={run_id} seed={seed}; "
                f"explicit {resolution}x{resolution} Float32 Copernicus network"
            ),
        }
    ]
    recipe_inputs = {
        "run_code": run_code,
        "lineage": f"{SKILL_ID}@{SKILL_VERSION} run={run_id} seed={seed}",
        "end_small_path": end_paths[0],
        "end_large_path": end_paths[1],
        "end_spots_path": end_paths[2],
        "candidate_index": candidate_index,
        "iterations": iterations,
        "iterations_per_step": iterations_per_step,
        "noise_element_size": noise_element_size,
        "noise_offset_x": noise_offsets[0],
        "noise_offset_y": noise_offsets[1],
        "activation_threshold": activation_threshold,
        "activation_width": activation_width,
        "contact_scale": spec["contact_scale"],
        "contact_output": str(contact_output),
        "selected_output": str(selected_output),
    }
    candidate_labels = ["Small Waves", "Large Waves", "Spots"]
    candidates = [
        {
            "id": preset,
            "label": candidate_labels[index],
            "model": "Gray-Scott",
            "preset": preset,
            "seed": seed,
            "lineage": f"{run_id}:{preset}:seed={seed}",
            "human_rating": {"score": None, "notes": "", "selected": False},
            "automatic_rank": None,
        }
        for index, preset in enumerate(REACTION_PRESETS)
    ]
    metadata = {
        "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
        "recipe": {"id": RECIPE_ID, "version": RECIPE_VERSION},
        "run_id": run_id,
        "seed": seed,
        "context": {"category": "Cop", "network_category": "CopNet", "path": network_path},
        "spec": spec,
        "candidates": candidates,
        "selection": {
            "method": "human",
            "preview_input": candidate_index,
            "winner": None,
            "automatic_ranking": False,
            "contact_order": list(REACTION_PRESETS),
        },
        "algorithm": {
            "model": "Gray-Scott",
            "mode": "deterministic_non_simulation",
            "compiled_cook": False,
            "live_simulation": False,
            "total_integration_steps": spec["total_steps"],
            "native_nodes": [
                "fractalnoise",
                "remap",
                "reactiondiffusion_block_begin",
                "reactiondiffusion_block_end",
                "monotorgb",
                "contactsheet",
            ],
            "python_image_compute": False,
        },
        "evidence": {
            "numeric_validation": str(validation_path),
            "contact_sheet": str(contact_output),
            "selected_image": str(selected_output),
            "graph_svg": str(graph_svg),
        },
        "references": [
            "https://www.sidefx.com/docs/houdini/copernicus/reaction_diffusion.html",
            "https://www.sidefx.com/docs/houdini/nodes/cop/reactiondiffusion_block_begin.html",
            "https://www.sidefx.com/docs/houdini/nodes/cop/reactiondiffusion_block_end.html",
        ],
        "license": {
            "mode": "houdini-apprentice-noncommercial",
            "commercial_use": False,
            "scene_extension": ".hipnc",
            "render_ceiling": [1280, 720],
        },
    }

    return [
        build_envelope(
            "graph.apply_batch",
            {
                "batch_id": f"{SKILL_ID}:{run_id}:network",
                "operations": network_operations,
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(network_log),
                "label": f"Hermes create Copernicus network {run_id}",
                "checkpoint_stem": f"reaction_{run_id}_network",
            },
            request_id=f"{run_id}-network",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "recipe.instantiate",
            {
                "recipe_id": RECIPE_ID,
                "version": RECIPE_VERSION,
                "parent_path": network_path,
                "batch_id": f"{SKILL_ID}:{run_id}:graph",
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(graph_log),
                "inputs": recipe_inputs,
                "label": f"Hermes {SKILL_ID} {run_id}",
                "checkpoint_stem": f"reaction_{run_id}_graph",
            },
            request_id=f"{run_id}-graph",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "cop.reaction.validate",
            {
                "network_path": network_path,
                "pattern_node_paths": end_paths,
                "contact_sheet_path": contact_sheet_path,
                "resolution": resolution,
                "iterations": iterations,
                "iterations_per_step": iterations_per_step,
                "candidate_index": candidate_index,
                "output_path": str(validation_path),
            },
            request_id=f"{run_id}-validate",
            policy=cook_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "cop.image.export",
            {
                "rop_path": contact_rop_path,
                "output_path": str(contact_output),
                "log_path": str(contact_export_log),
                "expected_resolution": list(spec["contact_resolution"]),
                "frame": 1.0,
            },
            request_id=f"{run_id}-contact-export",
            policy=export_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "cop.image.export",
            {
                "rop_path": selected_rop_path,
                "output_path": str(selected_output),
                "log_path": str(selected_export_log),
                "expected_resolution": [resolution, resolution],
                "frame": 1.0,
            },
            request_id=f"{run_id}-selected-export",
            policy=export_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_svg",
            {"node_path": network_path, "output_path": str(graph_svg), "max_nodes": 32},
            request_id=f"{run_id}-graph-svg",
            policy=cook_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "graph.capture_manifest",
            {
                "node_path": network_path,
                "output_path": str(graph_manifest),
                "public_parameters": {
                    network_path: ["setres", "res1", "res2", "setprecision", "precision"],
                    noise_path: ["elementsize", "offx", "offy", "oct", "rough"],
                    threshold_path: ["op", "threshold", "width"],
                    end_paths[0]: [
                        "model",
                        "presetsgs",
                        "simulate",
                        "iterations",
                        "iterationsperstep",
                        "continuouscook",
                        "cacheenabled",
                    ],
                    end_paths[1]: [
                        "model",
                        "presetsgs",
                        "simulate",
                        "iterations",
                        "iterationsperstep",
                        "continuouscook",
                        "cacheenabled",
                    ],
                    end_paths[2]: [
                        "model",
                        "presetsgs",
                        "simulate",
                        "iterations",
                        "iterationsperstep",
                        "continuouscook",
                        "cacheenabled",
                    ],
                    selector_path: ["input"],
                    contact_sheet_path: [],
                    selected_path: [],
                    contact_rop_path: ["trange", "copoutput", "docompile", "initsim"],
                    selected_rop_path: ["trange", "copoutput", "docompile", "initsim"],
                },
                "metric_node_paths": [],
                "metadata": metadata,
            },
            request_id=f"{run_id}-manifest",
            policy=cook_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "hip.save_snapshot",
            {"output_dir": str(scene_dir), "stem": f"reaction_{run_id}_final"},
            request_id=f"{run_id}-snapshot",
            policy=cook_policy,
            **common,
        ).as_dict(),
    ]


__all__ = ["plan"]
