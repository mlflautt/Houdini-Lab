"""Plan Sprint 18's native Copernicus-to-MaterialX three-swatch foundry."""

from __future__ import annotations

import re
from pathlib import Path

from hermes_houdini.material_foundry import FOUNDRY_CANDIDATES, validate_foundry_spec
from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "lookdev.procedural_material_foundry"
SKILL_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,23}\Z")


def _offsets(seed: int) -> tuple[float, float]:
    return round((seed % 997) / 31.0, 8), round(((seed * 29 + 17) % 991) / 37.0, 8)


def plan(
    artifact_dir: str,
    run_id: str = "material_foundry_001",
    seed: int = 18181,
    resolution: int = 512,
    candidate_index: int = 0,
    width: int = 960,
    height: int = 540,
    frame: float = 1.0,
    time_limit: float = 60.0,
    max_threads: int = 4,
    render_preview: bool = True,
) -> list[dict[str, object]]:
    """Return explicit pattern, PBR, swatch, USD, render, evidence, and snapshot calls."""
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-24 filename-safe characters")
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 2_147_483_647:
        raise ValueError("seed must be an integer between 0 and 2147483647")
    spec = validate_foundry_spec(resolution=resolution, candidate_index=candidate_index)
    if not isinstance(width, int) or not 1 <= width <= 1280:
        raise ValueError("width must be between 1 and 1280")
    if not isinstance(height, int) or not 1 <= height <= 720:
        raise ValueError("height must be between 1 and 720")

    run_code = run_id.upper().replace("-", "_")
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    network_path = f"/img/{run_code}_COPNET"
    swatch_geo_path = f"/obj/{run_code}_SWATCHES"
    stage_out = f"/stage/OUT_{run_code}_STAGE"
    preview_path = observation_dir / f"{run_id}_karma_cpu.png"
    validation_path = manifest_dir / f"{run_id}_pbr_channels.json"
    graph_manifest = manifest_dir / f"{run_id}_material_foundry_manifest.json"
    cop_svg = observation_dir / f"{run_id}_cop_graph.svg"
    lop_svg = observation_dir / f"{run_id}_lop_graph.svg"
    rop_path = f"/out/{run_code}_KARMA_PREVIEW"

    max_memory = 1_073_741_824
    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=45,
        max_primitives=10_000,
        max_memory_bytes=max_memory,
        max_resolution=(max(1024, width), max(1024, height)),
    )
    validate_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=120,
        max_primitives=10_000,
        max_memory_bytes=max_memory,
        max_resolution=(max(1024, width), max(1024, height)),
    )
    rop_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=max(45.0, time_limit),
        max_primitives=10_000,
        max_memory_bytes=max_memory,
        max_resolution=(width, height),
    )
    render_policy = Policy(
        risk=RiskClass.EXTERNAL,
        allow_external_process=True,
        max_seconds=time_limit,
        max_primitives=10_000,
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
    offsets = _offsets(seed)
    patterns = {
        "verdigris": f"{network_path}/{run_code}_SMALL_WAVES",
        "emberglaze": f"{network_path}/{run_code}_LARGE_WAVES",
        "moonlichen": f"{network_path}/{run_code}_SPOTS",
    }
    candidate_contracts = []
    for candidate in FOUNDRY_CANDIDATES:
        upper = candidate.upper()
        candidate_contracts.append(
            {
                "id": candidate,
                "channels": {
                    channel: f"{network_path}/OUT_{run_code}_{upper}_{channel.upper()}"
                    for channel in ("base_color", "roughness", "height", "normal")
                },
                "material": f"{network_path}/OUT_{run_code}_{upper}_USD_MATERIAL",
            }
        )
    swatch_sops = {
        candidate: f"{swatch_geo_path}/OUT_{run_code}_{candidate.upper()}_SWATCH"
        for candidate in FOUNDRY_CANDIDATES
    }
    materials = {
        candidate: f"/materials/{run_code}_{candidate}" for candidate in FOUNDRY_CANDIDATES
    }
    bindings = [
        {
            "candidate_id": "verdigris",
            "prim_path": "/World/Swatches/Verdigris",
            "material_path": materials["verdigris"],
        },
        {
            "candidate_id": "emberglaze",
            "prim_path": "/World/Swatches/Emberglaze",
            "material_path": materials["emberglaze"],
        },
        {
            "candidate_id": "moonlichen",
            "prim_path": "/World/Swatches/Moonlichen",
            "material_path": materials["moonlichen"],
        },
    ]

    calls = [
        build_envelope(
            "graph.apply_batch",
            {
                "batch_id": f"{SKILL_ID}:{run_id}:networks",
                "operations": [
                    {
                        "op": "create",
                        "ref": "copnet",
                        "parent_path": "/img",
                        "operator_type": "copnet",
                        "name": f"{run_code}_COPNET",
                        "exact_name": True,
                        "category": "CopNet",
                        "role": "procedural_material_foundry_network",
                        "position": [0, 0],
                        "parameters": {
                            "setres": 1,
                            "res": [resolution, resolution],
                            "setpixelscale": 1,
                            "pixelscale": 1.0,
                            "setprecision": 1,
                            "precision": 1,
                        },
                        "comment": f"{SKILL_ID}@{SKILL_VERSION}; seed={seed}; Float32 {resolution}x{resolution}",
                    },
                    {
                        "op": "create",
                        "ref": "swatches",
                        "parent_path": "/obj",
                        "operator_type": "geo",
                        "name": f"{run_code}_SWATCHES",
                        "exact_name": True,
                        "category": "Object",
                        "role": "material_foundry_swatch_network",
                        "position": [0, 0],
                        "parameters": {},
                        "comment": "Three equal editable comparison swatches",
                    },
                ],
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_networks.jsonl"),
                "label": f"Hermes create material foundry networks {run_id}",
                "checkpoint_stem": f"foundry_{run_id}_networks",
            },
            request_id=f"{run_id}-networks",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "recipe.instantiate",
            {
                "recipe_id": "cop.reaction_diffusion_pattern",
                "version": "1.0.0",
                "parent_path": network_path,
                "batch_id": f"{SKILL_ID}:{run_id}:patterns",
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_patterns.jsonl"),
                "inputs": {
                    "run_code": run_code,
                    "lineage": f"{SKILL_ID}@{SKILL_VERSION}; seed={seed}",
                    "end_small_path": patterns["verdigris"],
                    "end_large_path": patterns["emberglaze"],
                    "end_spots_path": patterns["moonlichen"],
                    "candidate_index": candidate_index,
                    "iterations": 6,
                    "iterations_per_step": 6,
                    "noise_element_size": 0.11,
                    "noise_offset_x": offsets[0],
                    "noise_offset_y": offsets[1],
                    "activation_threshold": 0.61,
                    "activation_width": 0.025,
                    "contact_scale": 0.5 if resolution >= 512 else 1.0,
                    "contact_output": str(observation_dir / f"{run_id}_pattern_contact.png"),
                    "selected_output": str(observation_dir / f"{run_id}_selected_pattern.png"),
                },
                "label": f"Hermes reusable patterns {run_id}",
                "checkpoint_stem": f"foundry_{run_id}_patterns",
            },
            request_id=f"{run_id}-patterns",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "recipe.instantiate",
            {
                "recipe_id": "cop.procedural_material_foundry",
                "version": "1.0.0",
                "parent_path": network_path,
                "batch_id": f"{SKILL_ID}:{run_id}:channels",
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_channels.jsonl"),
                "inputs": {
                    "run_code": run_code,
                    "lineage": f"{SKILL_ID}@{SKILL_VERSION}; seed={seed}",
                    "verdigris_pattern_path": patterns["verdigris"],
                    "emberglaze_pattern_path": patterns["emberglaze"],
                    "moonlichen_pattern_path": patterns["moonlichen"],
                },
                "label": f"Hermes PBR channels {run_id}",
                "checkpoint_stem": f"foundry_{run_id}_channels",
            },
            request_id=f"{run_id}-channels",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "cop.material_foundry.validate",
            {
                "network_path": network_path,
                "candidate_contracts": candidate_contracts,
                "resolution": resolution,
                "candidate_index": candidate_index,
                "output_path": str(validation_path),
            },
            request_id=f"{run_id}-channel-validate",
            policy=validate_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "recipe.instantiate",
            {
                "recipe_id": "sop.material_swatch_gallery",
                "version": "1.0.0",
                "parent_path": swatch_geo_path,
                "batch_id": f"{SKILL_ID}:{run_id}:swatches",
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_swatches.jsonl"),
                "inputs": {"run_code": run_code, "radius": 1.15, "spacing": 2.65},
                "label": f"Hermes swatch gallery {run_id}",
                "checkpoint_stem": f"foundry_{run_id}_swatches",
            },
            request_id=f"{run_id}-swatches",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "recipe.instantiate",
            {
                "recipe_id": "lop.procedural_material_foundry_stage",
                "version": "1.0.0",
                "parent_path": "/stage",
                "batch_id": f"{SKILL_ID}:{run_id}:stage",
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_stage.jsonl"),
                "inputs": {
                    "run_code": run_code,
                    "verdigris_sop_path": swatch_sops["verdigris"],
                    "emberglaze_sop_path": swatch_sops["emberglaze"],
                    "moonlichen_sop_path": swatch_sops["moonlichen"],
                    "verdigris_material_cop": candidate_contracts[0]["material"],
                    "emberglaze_material_cop": candidate_contracts[1]["material"],
                    "moonlichen_material_cop": candidate_contracts[2]["material"],
                    "render_picture": str(preview_path),
                    "width": width,
                    "height": height,
                },
                "label": f"Hermes material foundry stage {run_id}",
                "checkpoint_stem": f"foundry_{run_id}_stage",
            },
            request_id=f"{run_id}-stage",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "solaris.material_foundry.validate",
            {"stage_node_path": stage_out, "bindings": bindings, "max_prims": 10_000},
            request_id=f"{run_id}-stage-validate",
            policy=validate_policy,
            **common,
        ).as_dict(),
    ]
    if render_preview:
        calls.extend(
            [
                build_envelope(
                    "solaris.karma_rop.build",
                    {
                        "stage_node_path": stage_out,
                        "render_settings_path": f"/Render/{run_code}_Settings",
                        "output_path": str(preview_path),
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
                        "output_path": str(preview_path),
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
        "seed": seed,
        "spec": spec,
        "recipes": [
            "cop.reaction_diffusion_pattern@1.0.0",
            "cop.procedural_material_foundry@1.0.0",
            "sop.material_swatch_gallery@1.0.0",
            "lop.procedural_material_foundry_stage@1.0.0",
        ],
        "candidates": [
            {
                "id": candidate,
                "channels": candidate_contracts[index]["channels"],
                "material_path": materials[candidate],
                "human_rating": {"score": None, "notes": "", "selected": False},
                "automatic_rank": None,
            }
            for index, candidate in enumerate(FOUNDRY_CANDIDATES)
        ],
        "selection": {
            "method": "human",
            "preview_input": candidate_index,
            "winner": None,
            "automatic_ranking": False,
        },
        "render": {
            "requested": render_preview,
            "delegate": "BRAY_HdKarma",
            "resolution": [width, height],
            "frame": frame,
            "output": str(preview_path),
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
                {"node_path": network_path, "output_path": str(cop_svg), "max_nodes": 64},
                request_id=f"{run_id}-cop-svg",
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
                        f"/stage/{run_code}_TEXTURE_MATERIALS": [
                            "materials",
                            "matnode1",
                            "matnode2",
                            "matnode3",
                            "matpath1",
                            "matpath2",
                            "matpath3",
                        ],
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
                {"output_dir": str(scene_dir), "stem": f"material_foundry_{run_id}_final"},
                request_id=f"{run_id}-snapshot",
                policy=validate_policy,
                **common,
            ).as_dict(),
        ]
    )
    return calls
