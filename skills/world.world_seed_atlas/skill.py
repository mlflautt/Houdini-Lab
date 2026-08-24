"""Plan Sprint 19's native three-world HeightField and Karma atlas."""

from __future__ import annotations

import re
from pathlib import Path

from hermes_houdini.schemas.command import Policy, RiskClass
from hermes_houdini.world_seed import validate_world_seed_spec
from skills._lib import build_envelope

SKILL_ID = "world.world_seed_atlas"
SKILL_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,23}\Z")


def plan(
    artifact_dir: str,
    run_id: str = "world_seed_atlas_001",
    base_seed: int = 19019,
    terrain_samples: int = 128,
    world_size: float = 9.0,
    width: int = 768,
    height: int = 432,
    frame: float = 1.0,
    time_limit: float = 90.0,
    max_threads: int = 4,
    render_preview: bool = True,
) -> list[dict[str, object]]:
    """Return explicit native graph, validation, stage, render, evidence, and snapshot calls."""
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-24 filename-safe characters")
    spec = validate_world_seed_spec(
        base_seed=base_seed, terrain_samples=terrain_samples, world_size=world_size
    )
    if not isinstance(width, int) or not 1 <= width <= 1280:
        raise ValueError("width must be between 1 and 1280")
    if not isinstance(height, int) or not 1 <= height <= 720:
        raise ValueError("height must be between 1 and 720")
    if (
        not isinstance(max_threads, int)
        or isinstance(max_threads, bool)
        or not 1 <= max_threads <= 32
    ):
        raise ValueError("max_threads must be between 1 and 32")

    run_code = run_id.upper().replace("-", "_")
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    render_path = observation_dir / f"{run_id}_karma_cpu.png"
    validation_path = manifest_dir / f"{run_id}_world_validation.json"
    graph_manifest = manifest_dir / f"{run_id}_world_seed_manifest.json"
    obj_svg = observation_dir / f"{run_id}_obj_graph.svg"
    lop_svg = observation_dir / f"{run_id}_lop_graph.svg"
    stage_out = f"/stage/OUT_{run_code}_STAGE"
    rop_path = f"/out/{run_code}_KARMA_PREVIEW"

    max_memory = 2_147_483_648
    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=90,
        max_points=150_000,
        max_primitives=150_000,
        max_memory_bytes=max_memory,
        max_resolution=(max(terrain_samples, width), max(terrain_samples, height)),
    )
    validate_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=180,
        max_points=150_000,
        max_primitives=150_000,
        max_memory_bytes=max_memory,
        max_resolution=(max(terrain_samples, width), max(terrain_samples, height)),
    )
    rop_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=max(60.0, time_limit),
        max_points=150_000,
        max_primitives=150_000,
        max_memory_bytes=max_memory,
        max_resolution=(width, height),
    )
    render_policy = Policy(
        risk=RiskClass.EXTERNAL,
        allow_external_process=True,
        max_seconds=time_limit,
        max_points=150_000,
        max_primitives=150_000,
        max_memory_bytes=max_memory,
        max_frames=1,
        max_output_bytes=536_870_912,
        max_resolution=(width, height),
    )
    common = {
        "session_id": run_id,
        "project_id": SKILL_ID,
        "expected": {"skill": SKILL_ID, "skill_version": SKILL_VERSION, "run_id": run_id},
    }

    network_paths: dict[str, str] = {}
    world_paths: dict[str, str] = {}
    candidate_contracts = []
    create_networks = []
    for index, candidate in enumerate(spec["candidates"]):
        candidate_id = candidate["id"]
        candidate_code = f"{run_code}_{candidate_id.upper()}"
        network_path = f"/obj/{candidate_code}"
        network_paths[candidate_id] = network_path
        world_paths[candidate_id] = f"{network_path}/OUT_{candidate_code}_WORLD"
        create_networks.append(
            {
                "op": "create",
                "ref": candidate_id,
                "parent_path": "/obj",
                "operator_type": "geo",
                "name": candidate_code,
                "exact_name": True,
                "category": "Object",
                "role": f"world_seed_network_{candidate_id}",
                "position": [float((index - 1) * 4), 0.0],
                "parameters": {},
                "comment": (
                    f"{SKILL_ID}@{SKILL_VERSION}; {candidate_id}; seed={candidate['seed']}"
                ),
            }
        )
        candidate_contracts.append(
            {
                "id": candidate_id,
                "network_path": network_path,
                "base_path": f"{network_path}/{candidate_code}_HEIGHTFIELD_BASE",
                "noise_path": f"{network_path}/{candidate_code}_SEEDED_NOISE",
                "terrace_path": f"{network_path}/{candidate_code}_TERRACES",
                "terrain_path": f"{network_path}/OUT_{candidate_code}_TERRAIN",
                "points_path": f"{network_path}/OUT_{candidate_code}_BIOME_POINTS",
                "forms_path": f"{network_path}/OUT_{candidate_code}_BIOME_FORMS",
                "hero_path": f"{network_path}/OUT_{candidate_code}_HERO",
                "world_path": world_paths[candidate_id],
            }
        )

    calls = [
        build_envelope(
            "graph.apply_batch",
            {
                "batch_id": f"{SKILL_ID}:{run_id}:networks",
                "operations": create_networks,
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_networks.jsonl"),
                "label": f"Hermes create World Seed networks {run_id}",
                "checkpoint_stem": f"world_seed_{run_id}_networks",
            },
            request_id=f"{run_id}-networks",
            policy=graph_policy,
            **common,
        ).as_dict()
    ]

    for candidate in spec["candidates"]:
        candidate_id = candidate["id"]
        candidate_code = f"{run_code}_{candidate_id.upper()}"
        calls.append(
            build_envelope(
                "recipe.instantiate",
                {
                    "recipe_id": "sop.world_seed_biome",
                    "version": "1.0.0",
                    "parent_path": network_paths[candidate_id],
                    "batch_id": f"{SKILL_ID}:{run_id}:{candidate_id}",
                    "checkpoint_dir": str(checkpoint_dir),
                    "log_path": str(log_dir / f"{run_id}_{candidate_id}.jsonl"),
                    "inputs": {
                        "run_code": candidate_code,
                        "lineage": (
                            f"{SKILL_ID}@{SKILL_VERSION}; {candidate_id}; seed={candidate['seed']}"
                        ),
                        "terrain_samples": terrain_samples,
                        "world_size": world_size,
                        "seed": candidate["seed"],
                        "offset_x": candidate["noise_offset"][0],
                        "offset_y": candidate["noise_offset"][1],
                        "noise_amplitude": candidate["noise_amplitude"],
                        "noise_element_size": candidate["noise_element_size"],
                        "terrace_step_size": candidate["terrace_step_size"],
                        "scatter_count": candidate["scatter_count"],
                        "scatter_radius": candidate["scatter_radius"],
                        "hero_radius": candidate["hero_radius"],
                        "platonic_type": candidate["platonic_type"],
                        "translation_x": candidate["translation_x"],
                        "terrain_r": candidate["terrain_color"][0],
                        "terrain_g": candidate["terrain_color"][1],
                        "terrain_b": candidate["terrain_color"][2],
                        "accent_r": candidate["accent_color"][0],
                        "accent_g": candidate["accent_color"][1],
                        "accent_b": candidate["accent_color"][2],
                    },
                    "label": f"Hermes World Seed {candidate_id}",
                    "checkpoint_stem": f"world_seed_{run_id}_{candidate_id}",
                },
                request_id=f"{run_id}-{candidate_id}",
                policy=graph_policy,
                **common,
            ).as_dict()
        )

    calls.extend(
        [
            build_envelope(
                "world_seed.validate",
                {
                    "candidate_contracts": candidate_contracts,
                    "base_seed": base_seed,
                    "terrain_samples": terrain_samples,
                    "world_size": world_size,
                    "output_path": str(validation_path),
                },
                request_id=f"{run_id}-validate",
                policy=validate_policy,
                **common,
            ).as_dict(),
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
                        "amber_sop_path": world_paths["amber_mesa"],
                        "verdant_sop_path": world_paths["verdant_rift"],
                        "lunar_sop_path": world_paths["lunar_basin"],
                        "render_picture": str(render_path),
                        "width": width,
                        "height": height,
                    },
                    "label": f"Hermes World Seed Atlas stage {run_id}",
                    "checkpoint_stem": f"world_seed_{run_id}_stage",
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
                    policy=rop_policy,
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
                    policy=render_policy,
                    **common,
                ).as_dict(),
            ]
        )

    metadata = {
        "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
        "run_id": run_id,
        "spec": spec,
        "recipes": ["sop.world_seed_biome@1.0.0", "lop.world_seed_atlas_stage@1.0.0"],
        "candidates": [
            {
                "id": candidate["id"],
                "seed": candidate["seed"],
                "world_path": world_paths[candidate["id"]],
                "human_rating": candidate["human_rating"],
                "automatic_rank": None,
            }
            for candidate in spec["candidates"]
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
            "watermarked_render": True,
        },
    }
    calls.extend(
        [
            build_envelope(
                "graph.capture_svg",
                {"node_path": "/obj", "output_path": str(obj_svg), "max_nodes": 96},
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
                    "public_parameters": {
                        f"/stage/{run_code}_CAMERA": [
                            "tx",
                            "ty",
                            "tz",
                            "rx",
                            "ry",
                            "rz",
                            "focalLength",
                        ],
                        f"/stage/{run_code}_KARMA_SETTINGS": [
                            "camera",
                            "resolutionx",
                            "samplesperpixel",
                            "pathtracedsamples",
                        ],
                    },
                    "metadata": metadata,
                },
                request_id=f"{run_id}-manifest",
                policy=validate_policy,
                **common,
            ).as_dict(),
            build_envelope(
                "hip.save_snapshot",
                {"output_dir": str(scene_dir), "stem": f"world_seed_atlas_{run_id}_final"},
                request_id=f"{run_id}-snapshot",
                policy=validate_policy,
                **common,
            ).as_dict(),
        ]
    )
    return calls
