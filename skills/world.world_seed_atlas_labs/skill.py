"""Plan Sprint 21's reversible SideFX Labs enhancement of the native World Seed Atlas."""

from __future__ import annotations

import re
from pathlib import Path

from hermes_houdini.labs_atlas import validate_labs_atlas_spec
from hermes_houdini.schemas.command import Policy, RiskClass
from hermes_houdini.skill_loader import load_skill
from skills._lib import build_envelope

SKILL_ID = "world.world_seed_atlas_labs"
SKILL_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,23}\Z")


def plan(
    artifact_dir: str,
    run_id: str = "labs_atlas_001",
    base_seed: int = 19019,
    terrain_samples: int = 96,
    world_size: float = 9.0,
    labs_available: bool = False,
    width: int = 768,
    height: int = 432,
    frame: float = 1.0,
    time_limit: float = 120.0,
    max_threads: int = 4,
    render_preview: bool = True,
) -> list[dict[str, object]]:
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-24 filename-safe characters")
    if not isinstance(labs_available, bool):
        raise ValueError("labs_available must be boolean")
    if not isinstance(width, int) or not 1 <= width <= 1280:
        raise ValueError("width must be between 1 and 1280")
    if not isinstance(height, int) or not 1 <= height <= 720:
        raise ValueError("height must be between 1 and 720")
    spec = validate_labs_atlas_spec(
        base_seed=base_seed,
        terrain_samples=terrain_samples,
        world_size=world_size,
        labs_available=labs_available,
    )
    native_spec = spec["native_spec"]
    run_code = run_id.upper().replace("-", "_")
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    render_path = observation_dir / f"{run_id}_karma_cpu.png"
    validation_path = manifest_dir / f"{run_id}_labs_atlas_validation.json"
    graph_manifest = manifest_dir / f"{run_id}_labs_atlas_manifest.json"
    obj_svg = observation_dir / f"{run_id}_obj_graph.svg"
    lop_svg = observation_dir / f"{run_id}_lop_graph.svg"
    stage_out = f"/stage/OUT_{run_code}_STAGE"
    rop_path = f"/out/{run_code}_KARMA_PREVIEW"

    max_memory = 2_147_483_648
    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=120,
        max_points=300_000,
        max_primitives=300_000,
        max_memory_bytes=max_memory,
        max_resolution=(max(terrain_samples, width), max(terrain_samples, height)),
    )
    validate_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=180,
        max_points=300_000,
        max_primitives=300_000,
        max_memory_bytes=max_memory,
        max_resolution=(max(terrain_samples, width), max(terrain_samples, height)),
    )
    common = {
        "session_id": run_id,
        "project_id": SKILL_ID,
        "expected": {"skill": SKILL_ID, "skill_version": SKILL_VERSION, "run_id": run_id},
    }

    # The native skill remains a real composable sub-skill. Reuse only its network,
    # three SOP recipes, and native validation; construct a new stage and evidence set.
    native_skill = load_skill(Path(__file__).resolve().parents[1] / "world.world_seed_atlas")
    native_calls = native_skill.plan(
        artifact_dir=str(artifacts),
        run_id=run_id,
        base_seed=base_seed,
        terrain_samples=terrain_samples,
        world_size=world_size,
        width=width,
        height=height,
        frame=frame,
        time_limit=time_limit,
        max_threads=max_threads,
        render_preview=False,
    )
    calls: list[dict[str, object]] = native_calls[:5]
    candidate_contracts = []
    comparison_paths: dict[str, str] = {}
    overlay_recipe = (
        "sop.world_seed_labs_enhancement"
        if labs_available
        else "sop.world_seed_labs_unavailable"
    )

    for candidate in native_spec["candidates"]:
        candidate_id = candidate["id"]
        candidate_code = f"{run_code}_{candidate_id.upper()}"
        network_path = f"/obj/{candidate_code}"
        comparison_path = f"{network_path}/OUT_{candidate_code}_NATIVE_LABS_COMPARE"
        comparison_paths[candidate_id] = comparison_path
        inputs: dict[str, object] = {"run_code": candidate_code}
        if labs_available:
            inputs.update(
                {
                    "native_shift": -2.25,
                    "labs_translation_x": float(candidate["translation_x"]) + 2.25,
                    "candidate_index": 0,
                    "pscale_min": 0.65,
                    "pscale_max": 1.25,
                    "attribute_seed": int(candidate["seed"]) + 401,
                }
            )
        calls.append(
            build_envelope(
                "recipe.instantiate",
                {
                    "recipe_id": overlay_recipe,
                    "version": "1.0.0",
                    "parent_path": network_path,
                    "batch_id": f"{SKILL_ID}:{run_id}:{candidate_id}:overlay",
                    "checkpoint_dir": str(checkpoint_dir),
                    "log_path": str(log_dir / f"{run_id}_{candidate_id}_overlay.jsonl"),
                    "inputs": inputs,
                    "label": f"Hermes optional Labs overlay {candidate_id}",
                    "checkpoint_stem": f"labs_atlas_{run_id}_{candidate_id}",
                },
                request_id=f"{run_id}-{candidate_id}-overlay",
                policy=graph_policy,
                **common,
            ).as_dict()
        )
        contract = {
            "id": candidate_id,
            "network_path": network_path,
            "native_world_path": f"{network_path}/OUT_{candidate_code}_WORLD",
            "selector_path": (
                f"{network_path}/{candidate_code}_SELECT_NATIVE_OR_LABS"
                if labs_available
                else f"{network_path}/{candidate_code}_SELECT_NATIVE_ONLY"
            ),
            "selected_path": f"{network_path}/OUT_{candidate_code}_SELECTED_WORLD",
            "comparison_path": comparison_path,
        }
        if labs_available:
            contract.update(
                {
                    "terrain_analysis_path": f"{network_path}/{candidate_code}_LABS_TERRAIN_ANALYSIS",
                    "curvature_path": f"{network_path}/{candidate_code}_LABS_CURVATURE",
                    "instance_attributes_path": f"{network_path}/{candidate_code}_LABS_INSTANCE_ATTRIBUTES",
                    "labs_world_path": f"{network_path}/OUT_{candidate_code}_LABS_WORLD",
                }
            )
        else:
            contract["unavailable_path"] = f"{network_path}/OPTIONAL_LABS_UNAVAILABLE"
        candidate_contracts.append(contract)

    calls.append(
        build_envelope(
            "world_seed.labs.validate",
            {
                "candidate_contracts": candidate_contracts,
                "base_seed": base_seed,
                "terrain_samples": terrain_samples,
                "world_size": world_size,
                "labs_available": labs_available,
                "output_path": str(validation_path),
                "max_points": 300_000,
                "max_primitives": 300_000,
                "max_seconds": 180.0,
            },
            request_id=f"{run_id}-labs-validate",
            policy=validate_policy,
            **common,
        ).as_dict()
    )
    calls.extend(
        [
            build_envelope(
                "recipe.instantiate",
                {
                    "recipe_id": "lop.world_seed_atlas_stage",
                    "version": "1.0.0",
                    "parent_path": "/stage",
                    "batch_id": f"{SKILL_ID}:{run_id}:stage",
                    "checkpoint_dir": str(checkpoint_dir),
                    "log_path": str(log_dir / f"{run_id}_stage.jsonl"),
                    "inputs": {
                        "run_code": run_code,
                        "amber_sop_path": comparison_paths["amber_mesa"],
                        "verdant_sop_path": comparison_paths["verdant_rift"],
                        "lunar_sop_path": comparison_paths["lunar_basin"],
                        "render_picture": str(render_path),
                        "width": width,
                        "height": height,
                        "camera_tz": 80.0,
                    },
                    "label": f"Hermes Labs World Seed Atlas stage {run_id}",
                    "checkpoint_stem": f"labs_atlas_{run_id}_stage",
                },
                request_id=f"{run_id}-stage",
                policy=graph_policy,
                **common,
            ).as_dict(),
            build_envelope(
                "solaris.world_seed.validate",
                {
                    "stage_node_path": stage_out,
                    "prim_paths": [
                        "/World/WorldSeeds/AmberMesa",
                        "/World/WorldSeeds/VerdantRift",
                        "/World/WorldSeeds/LunarBasin",
                    ],
                    "max_prims": 25_000,
                },
                request_id=f"{run_id}-stage-validate",
                policy=validate_policy,
                **common,
            ).as_dict(),
        ]
    )
    if render_preview:
        calls.extend(
            [
                build_envelope(
                    "solaris.karma_rop.build",
                    {
                        "stage_node_path": stage_out,
                        "render_settings_path": f"/Render/{run_code}_Settings",
                        "output_path": str(render_path),
                        "checkpoint_dir": str(checkpoint_dir),
                        "log_path": str(log_dir / f"{run_id}_karma_rop.jsonl"),
                        "node_name": f"{run_code}_KARMA_PREVIEW",
                        "width": width,
                        "height": height,
                        "frame": frame,
                        "time_limit": time_limit,
                        "max_threads": max_threads,
                    },
                    request_id=f"{run_id}-karma-rop",
                    policy=Policy(
                        risk=RiskClass.MEDIUM,
                        max_seconds=max(60.0, time_limit),
                        max_points=300_000,
                        max_primitives=300_000,
                        max_memory_bytes=max_memory,
                        max_resolution=(width, height),
                    ),
                    **common,
                ).as_dict(),
                build_envelope(
                    "render.karma.preview",
                    {
                        "rop_path": rop_path,
                        "output_path": str(render_path),
                        "log_path": str(log_dir / f"{run_id}_karma_render.jsonl"),
                        "frame": frame,
                    },
                    request_id=f"{run_id}-karma-render",
                    policy=Policy(
                        risk=RiskClass.EXTERNAL,
                        allow_external_process=True,
                        max_seconds=time_limit,
                        max_points=300_000,
                        max_primitives=300_000,
                        max_memory_bytes=max_memory,
                        max_frames=1,
                        max_output_bytes=536_870_912,
                        max_resolution=(width, height),
                    ),
                    **common,
                ).as_dict(),
            ]
        )

    metadata = {
        "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
        "run_id": run_id,
        "spec": spec,
        "capability_input": {"labs_available": labs_available, "explicit": True},
        "recipes": [
            "sop.world_seed_biome@1.0.0",
            f"{overlay_recipe}@1.0.0",
            "lop.world_seed_atlas_stage@1.0.0",
        ],
        "selection": spec["selection"],
        "render": {
            "requested": render_preview,
            "delegate": "BRAY_HdKarma",
            "resolution": [width, height],
            "frame": frame,
            "output": str(render_path),
        },
        "license": {
            "mode": "houdini-apprentice-noncommercial",
            "scene_extension": ".hipnc",
            "render_ceiling": [1280, 720],
        },
    }
    calls.extend(
        [
            build_envelope(
                "graph.capture_svg",
                {"node_path": "/obj", "output_path": str(obj_svg), "max_nodes": 180},
                request_id=f"{run_id}-obj-svg",
                policy=validate_policy,
                **common,
            ).as_dict(),
            build_envelope(
                "graph.capture_svg",
                {"node_path": "/stage", "output_path": str(lop_svg), "max_nodes": 64},
                request_id=f"{run_id}-lop-svg",
                policy=validate_policy,
                **common,
            ).as_dict(),
            build_envelope(
                "graph.capture_manifest",
                {
                    "node_path": "/stage",
                    "output_path": str(graph_manifest),
                    "metric_node_paths": list(comparison_paths.values()),
                    "metadata": metadata,
                },
                request_id=f"{run_id}-manifest",
                policy=validate_policy,
                **common,
            ).as_dict(),
            build_envelope(
                "hip.save_snapshot",
                {"output_dir": str(scene_dir), "stem": f"labs_world_seed_atlas_{run_id}_final"},
                request_id=f"{run_id}-snapshot",
                policy=validate_policy,
                **common,
            ).as_dict(),
        ]
    )
    return calls
