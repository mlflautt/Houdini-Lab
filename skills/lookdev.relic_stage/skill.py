"""Plan an editable Solaris relic stage and optional bounded Karma CPU preview."""

from __future__ import annotations

import re
from pathlib import Path

from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "lookdev.relic_stage"
SKILL_VERSION = "1.0.0"
RECIPE_ID = "lop.relic_lookdev_stage"
RECIPE_VERSION = "1.0.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,23}\Z")


def plan(
    source_sop_path: str,
    artifact_dir: str,
    run_id: str = "relic_lookdev_001",
    stage_parent_path: str = "/stage",
    asset_prim_path: str = "/World/Asset",
    candidate_index: int = 0,
    width: int = 640,
    height: int = 360,
    frame: float = 1.0,
    time_limit: float = 30.0,
    max_threads: int = 4,
    render_preview: bool = True,
) -> list[dict[str, object]]:
    """Return graph, MaterialX, USD validation, preview, observation, and snapshot calls."""
    if not source_sop_path.startswith("/") or source_sop_path == "/":
        raise ValueError("source_sop_path must be an absolute SOP node path")
    if stage_parent_path != "/stage":
        raise ValueError("Sprint 8 is intentionally bounded to the explicit /stage LOP network")
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-24 filename-safe characters")

    run_code = run_id.upper().replace("-", "_")
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    preview_path = observation_dir / f"{run_id}_karma_cpu.png"
    graph_log = log_dir / f"{run_id}_lop_graph.jsonl"
    material_log = log_dir / f"{run_id}_materialx.jsonl"
    rop_log = log_dir / f"{run_id}_karma_rop.jsonl"
    render_log = log_dir / f"{run_id}_karma_render.jsonl"
    graph_svg = observation_dir / f"{run_id}_lop_graph.svg"
    graph_manifest = manifest_dir / f"{run_id}_lookdev_manifest.json"

    library_path = f"/stage/{run_code}_MATERIALS"
    selector_path = f"/stage/{run_code}_SELECT_MATERIAL"
    stage_output_path = f"/stage/OUT_{run_code}_STAGE"
    camera_lop_path = f"/stage/{run_code}_CAMERA"
    settings_lop_path = f"/stage/{run_code}_KARMA_SETTINGS"
    camera_prim_path = f"/cameras/{run_code}_Camera"
    light_prim_path = f"/lights/{run_code}_Dome"
    render_settings_path = f"/Render/{run_code}_Settings"
    rop_path = f"/out/{run_code}_KARMA_PREVIEW"

    materials = [
        {
            "id": "oxide",
            "builder_name": f"{run_code}_OXIDE_MTLX",
            "material_path": f"/materials/{run_code}_oxide",
            "base_color": [0.045, 0.16, 0.2],
            "metalness": 0.82,
            "roughness": 0.31,
        },
        {
            "id": "amber",
            "builder_name": f"{run_code}_AMBER_MTLX",
            "material_path": f"/materials/{run_code}_amber",
            "base_color": [0.72, 0.19, 0.035],
            "metalness": 0.08,
            "roughness": 0.24,
        },
        {
            "id": "ivory",
            "builder_name": f"{run_code}_IVORY_MTLX",
            "material_path": f"/materials/{run_code}_ivory",
            "base_color": [0.76, 0.69, 0.52],
            "metalness": 0.0,
            "roughness": 0.46,
        },
    ]
    max_prims = 10_000
    max_memory = 1_073_741_824
    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=30,
        max_primitives=max_prims,
        max_memory_bytes=max_memory,
        max_resolution=(width, height),
    )
    rop_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=max(30.0, time_limit),
        max_primitives=max_prims,
        max_memory_bytes=max_memory,
        max_resolution=(width, height),
    )
    stage_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=30,
        max_primitives=max_prims,
        max_memory_bytes=max_memory,
        max_resolution=(width, height),
    )
    render_policy = Policy(
        risk=RiskClass.EXTERNAL,
        allow_external_process=True,
        max_seconds=time_limit,
        max_primitives=max_prims,
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
    calls = [
        build_envelope(
            "recipe.instantiate",
            {
                "recipe_id": RECIPE_ID,
                "version": RECIPE_VERSION,
                "parent_path": stage_parent_path,
                "batch_id": f"{SKILL_ID}:{run_id}",
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(graph_log),
                "inputs": {
                    "source_sop_path": source_sop_path,
                    "run_code": run_code,
                    "asset_prim_path": asset_prim_path,
                    "candidate_index": candidate_index,
                    "render_picture": str(preview_path),
                    "width": width,
                    "height": height,
                },
                "label": f"Hermes {SKILL_ID} {run_id}",
                "checkpoint_stem": f"lookdev_{run_id}",
            },
            request_id=f"{run_id}-lop-graph",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "solaris.materialx.populate",
            {
                "material_library_path": library_path,
                "materials": materials,
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(material_log),
            },
            request_id=f"{run_id}-materialx",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "solaris.stage.validate",
            {
                "stage_node_path": stage_output_path,
                "expected_paths": [
                    asset_prim_path,
                    *[material["material_path"] for material in materials],
                    light_prim_path,
                    camera_prim_path,
                    render_settings_path,
                ],
                "binding_prim_path": asset_prim_path,
                "max_prims": max_prims,
                "frame": frame,
            },
            request_id=f"{run_id}-usd-validate",
            policy=stage_policy,
            **common,
        ).as_dict(),
    ]
    if render_preview:
        calls.extend(
            [
                build_envelope(
                    "solaris.karma_rop.build",
                    {
                        "stage_node_path": stage_output_path,
                        "render_settings_path": render_settings_path,
                        "output_path": str(preview_path),
                        "checkpoint_dir": str(checkpoint_dir),
                        "log_path": str(rop_log),
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
                        "log_path": str(render_log),
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
        "recipe": {"id": RECIPE_ID, "version": RECIPE_VERSION},
        "run_id": run_id,
        "source_sop_path": source_sop_path,
        "usd_contract": {
            "asset": asset_prim_path,
            "camera": camera_prim_path,
            "light": light_prim_path,
            "render_settings": render_settings_path,
            "stage_output": stage_output_path,
        },
        "materials": [
            {
                **material,
                "human_rating": {"score": None, "notes": "", "selected": False},
                "automatic_rank": None,
            }
            for material in materials
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
            "time_limit": time_limit,
            "max_threads": max_threads,
            "output": str(preview_path),
        },
        "license": {
            "mode": "houdini-apprentice-noncommercial",
            "commercial_use": False,
            "scene_extension": ".hipnc",
            "render_ceiling": [1280, 720],
            "watermarked_render": True,
        },
    }
    calls.extend(
        [
            build_envelope(
                "graph.capture_svg",
                {"node_path": stage_parent_path, "output_path": str(graph_svg), "max_nodes": 32},
                request_id=f"{run_id}-graph-svg",
                policy=stage_policy,
                **common,
            ).as_dict(),
            build_envelope(
                "graph.capture_manifest",
                {
                    "node_path": stage_parent_path,
                    "output_path": str(graph_manifest),
                    "public_parameters": {
                        selector_path: ["input"],
                        camera_lop_path: [
                            "primpath",
                            "tx",
                            "ty",
                            "tz",
                            "rx",
                            "ry",
                            "rz",
                            "focalLength",
                        ],
                        settings_lop_path: [
                            "primpath",
                            "camera",
                            "resolutionx",
                            "resolutiony",
                            "samplesperpixel",
                            "pathtracedsamples",
                        ],
                    },
                    "metadata": metadata,
                },
                request_id=f"{run_id}-manifest",
                policy=stage_policy,
                **common,
            ).as_dict(),
            build_envelope(
                "hip.save_snapshot",
                {"output_dir": str(scene_dir), "stem": f"lookdev_{run_id}_final"},
                request_id=f"{run_id}-snapshot",
                policy=stage_policy,
                **common,
            ).as_dict(),
        ]
    )
    return calls
