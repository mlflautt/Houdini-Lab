"""Plan the verified kinetic contracts and Sprint 23's layered presentation."""

from __future__ import annotations

import re
from pathlib import Path

from hermes_houdini.kinetic import validate_kinetic_spec
from hermes_houdini.schemas.command import Policy, RiskClass
from skills._lib import build_envelope

SKILL_ID = "motion.kinetic_reliquary"
SKILL_VERSION = "1.1.0"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,23}\Z")


def plan(
    artifact_dir: str,
    run_id: str = "kinetic_reliquary_001",
    seed: int = 22012,
    copy_count: int = 24,
    start_frame: int = 1,
    end_frame: int = 24,
    mops_available: bool = False,
    width: int = 640,
    height: int = 360,
    time_limit: float = 90.0,
    max_threads: int = 4,
    render_preview: bool = True,
) -> list[dict[str, object]]:
    artifacts = Path(artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("artifact_dir must be absolute")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-24 filename-safe characters")
    if not isinstance(width, int) or not 1 <= width <= 1280:
        raise ValueError("width must be between 1 and 1280")
    if not isinstance(height, int) or not 1 <= height <= 720:
        raise ValueError("height must be between 1 and 720")
    if not isinstance(max_threads, int) or not 1 <= max_threads <= 32:
        raise ValueError("max_threads must be between 1 and 32")
    spec = validate_kinetic_spec(
        seed=seed,
        copy_count=copy_count,
        start_frame=start_frame,
        end_frame=end_frame,
        mops_available=mops_available,
    )
    run_code = run_id.upper().replace("-", "_")
    network_path = f"/obj/{run_code}"
    base_packed_path = f"{network_path}/OUT_{run_code}_PACKED_RELICS"
    native_path = f"{network_path}/OUT_{run_code}_NATIVE"
    selector_path = f"{network_path}/{run_code}_SELECT_KINETIC"
    selected_path = f"{network_path}/OUT_{run_code}_SELECTED"
    comparison_path = f"{network_path}/OUT_{run_code}_KINETIC_COMPARE"
    presentation_path = f"{network_path}/OUT_{run_code}_KINETIC_STAGED"
    stage_path = f"/stage/OUT_{run_code}_STAGED_STAGE"
    checkpoint_dir = artifacts / "checkpoints"
    log_dir = artifacts / "logs"
    observation_dir = artifacts / "observations"
    manifest_dir = artifacts / "manifests"
    scene_dir = artifacts / "scenes"
    validation_path = manifest_dir / f"{run_id}_kinetic_validation.json"
    presentation_validation_path = manifest_dir / f"{run_id}_presentation_validation.json"
    visual_path = manifest_dir / f"{run_id}_visual_verification.json"
    graph_manifest = manifest_dir / f"{run_id}_kinetic_manifest.json"
    obj_svg = observation_dir / f"{run_id}_obj_graph.svg"
    lop_svg = observation_dir / f"{run_id}_lop_graph.svg"
    render_paths = {
        frame: observation_dir / f"{run_id}_f{frame:03d}_karma_cpu.png"
        for frame in spec["sample_frames"]
    }

    max_memory = 1_073_741_824
    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=120,
        max_points=20_000,
        max_primitives=20_000,
        max_memory_bytes=max_memory,
        max_frames=end_frame - start_frame + 1,
        max_resolution=(width, height),
    )
    validate_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=120,
        max_points=20_000,
        max_primitives=20_000,
        max_memory_bytes=max_memory,
        max_frames=end_frame - start_frame + 1,
        max_resolution=(width, height),
    )
    common = {
        "session_id": run_id,
        "project_id": SKILL_ID,
        "expected": {"skill": SKILL_ID, "skill_version": SKILL_VERSION, "run_id": run_id},
    }
    overlay_recipe = (
        "sop.kinetic_reliquary_mops"
        if mops_available
        else "sop.kinetic_reliquary_mops_unavailable"
    )
    presentation_recipe = (
        "sop.kinetic_reliquary_staged"
        if mops_available
        else "sop.kinetic_reliquary_staged_native"
    )
    calls = [
        build_envelope(
            "graph.apply_batch",
            {
                "batch_id": f"{SKILL_ID}:{run_id}:network",
                "operations": [
                    {
                        "op": "create",
                        "ref": "kinetic",
                        "parent_path": "/obj",
                        "operator_type": "geo",
                        "name": run_code,
                        "exact_name": True,
                        "category": "Object",
                        "role": "kinetic_reliquary_network",
                        "position": [0.0, 0.0],
                        "parameters": {},
                        "comment": f"{SKILL_ID}@{SKILL_VERSION}; seed={seed}; copies={copy_count}",
                    }
                ],
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_network.jsonl"),
                "label": f"Hermes create kinetic reliquary {run_id}",
                "checkpoint_stem": f"kinetic_{run_id}_network",
            },
            request_id=f"{run_id}-network",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "recipe.instantiate",
            {
                "recipe_id": "sop.kinetic_reliquary_native",
                "version": "1.0.0",
                "parent_path": network_path,
                "batch_id": f"{SKILL_ID}:{run_id}:native",
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_native.jsonl"),
                "inputs": {"run_code": run_code, "copy_count": copy_count, "radius": 3.0, "seed": seed},
                "label": f"Hermes native kinetic reliquary {run_id}",
                "checkpoint_stem": f"kinetic_{run_id}_native",
            },
            request_id=f"{run_id}-native",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "recipe.instantiate",
            {
                "recipe_id": overlay_recipe,
                "version": "1.0.0",
                "parent_path": network_path,
                "batch_id": f"{SKILL_ID}:{run_id}:optional",
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_optional.jsonl"),
                "inputs": ({"run_code": run_code, "seed": seed, "candidate_index": 0} if mops_available else {"run_code": run_code}),
                "label": f"Hermes optional MOPs kinetic branches {run_id}",
                "checkpoint_stem": f"kinetic_{run_id}_optional",
            },
            request_id=f"{run_id}-optional",
            policy=graph_policy,
            **common,
        ).as_dict(),
        build_envelope(
            "recipe.instantiate",
            {
                "recipe_id": presentation_recipe,
                "version": "1.0.0",
                "parent_path": network_path,
                "batch_id": f"{SKILL_ID}:{run_id}:presentation",
                "checkpoint_dir": str(checkpoint_dir),
                "log_path": str(log_dir / f"{run_id}_presentation.jsonl"),
                "inputs": {"run_code": run_code},
                "label": f"Hermes staged kinetic presentation {run_id}",
                "checkpoint_stem": f"kinetic_{run_id}_presentation",
            },
            request_id=f"{run_id}-presentation",
            policy=graph_policy,
            **common,
        ).as_dict(),
    ]
    validation_arguments: dict[str, object] = {
        "network_path": network_path,
        "base_packed_path": base_packed_path,
        "native_path": native_path,
        "selector_path": selector_path,
        "selected_path": selected_path,
        "comparison_path": comparison_path,
        "seed": seed,
        "copy_count": copy_count,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "mops_available": mops_available,
        "output_path": str(validation_path),
        "max_points": 20_000,
        "max_primitives": 20_000,
        "max_seconds": 120.0,
    }
    if mops_available:
        validation_arguments.update(
            {
                "branch_paths": {
                    "mops_plain": f"{network_path}/OUT_{run_code}_MOPS_PLAIN",
                    "mops_noise": f"{network_path}/OUT_{run_code}_MOPS_NOISE",
                    "mops_shape": f"{network_path}/OUT_{run_code}_MOPS_SHAPE",
                },
            }
        )
    else:
        validation_arguments["unavailable_path"] = f"{network_path}/OPTIONAL_MOPS_UNAVAILABLE"
    calls.append(
        build_envelope(
            "motion.kinetic_reliquary.validate",
            validation_arguments,
            request_id=f"{run_id}-validate",
            policy=validate_policy,
            **common,
        ).as_dict()
    )
    calls.append(
        build_envelope(
            "motion.kinetic_reliquary.presentation.validate",
            {
                "network_path": network_path,
                "presentation_path": presentation_path,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "mops_available": mops_available,
                "output_path": str(presentation_validation_path),
                "max_points": 20_000,
                "max_primitives": 20_000,
                "max_seconds": 120.0,
            },
            request_id=f"{run_id}-presentation-validate",
            policy=validate_policy,
            **common,
        ).as_dict()
    )
    first_render = render_paths[spec["sample_frames"][0]]
    calls.extend(
        [
            build_envelope(
                "recipe.instantiate",
                {
                    "recipe_id": "lop.kinetic_reliquary_staged_stage",
                    "version": "1.0.0",
                    "parent_path": "/stage",
                    "batch_id": f"{SKILL_ID}:{run_id}:stage",
                    "checkpoint_dir": str(checkpoint_dir),
                    "log_path": str(log_dir / f"{run_id}_stage.jsonl"),
                    "inputs": {"run_code": run_code, "gallery_sop_path": presentation_path, "render_picture": str(first_render), "width": width, "height": height},
                    "label": f"Hermes kinetic reliquary stage {run_id}",
                    "checkpoint_stem": f"kinetic_{run_id}_stage",
                },
                request_id=f"{run_id}-stage",
                policy=graph_policy,
                **common,
            ).as_dict(),
            build_envelope(
                "solaris.kinetic_reliquary.validate",
                {"stage_node_path": stage_path, "prim_path": "/World/StagedKineticReliquary", "max_prims": 10_000},
                request_id=f"{run_id}-stage-validate",
                policy=validate_policy,
                **common,
            ).as_dict(),
        ]
    )
    if render_preview:
        for frame, render_path in render_paths.items():
            suffix = f"F{frame:03d}"
            rop_path = f"/out/{run_code}_KARMA_{suffix}"
            calls.extend(
                [
                    build_envelope(
                        "solaris.karma_rop.build",
                        {"stage_node_path": stage_path, "render_settings_path": f"/Render/{run_code}_StagedSettings", "output_path": str(render_path), "checkpoint_dir": str(checkpoint_dir), "log_path": str(log_dir / f"{run_id}_{suffix}_rop.jsonl"), "node_name": f"{run_code}_KARMA_{suffix}", "width": width, "height": height, "frame": float(frame), "time_limit": time_limit, "max_threads": max_threads},
                        request_id=f"{run_id}-{suffix}-rop",
                        policy=graph_policy,
                        **common,
                    ).as_dict(),
                    build_envelope(
                        "render.karma.preview",
                        {"rop_path": rop_path, "output_path": str(render_path), "log_path": str(log_dir / f"{run_id}_{suffix}_render.jsonl"), "frame": float(frame)},
                        request_id=f"{run_id}-{suffix}-render",
                        policy=Policy(risk=RiskClass.EXTERNAL, allow_external_process=True, max_seconds=time_limit, max_points=20_000, max_primitives=20_000, max_memory_bytes=max_memory, max_frames=1, max_output_bytes=536_870_912, max_resolution=(width, height)),
                        **common,
                    ).as_dict(),
                ]
            )
        calls.append(
            build_envelope(
                "visual.analyze",
                {
                    "image_paths": [str(path) for path in render_paths.values()],
                    "output_path": str(visual_path),
                    "panel_count": 4 if mops_available else 1,
                    "panel_rows": 1,
                    "expect_motion": True,
                },
                request_id=f"{run_id}-visual",
                policy=validate_policy,
                **common,
            ).as_dict()
        )
    calls.append(
        build_envelope(
            "cook.node",
            {
                "node_path": presentation_path,
                "scope": "single_node",
                "frame": None,
                "force": False,
                "estimate": {
                    "points": copy_count * (80 if mops_available else 1),
                    "primitives": copy_count * (80 if mops_available else 1),
                    "memory_bytes": 134_217_728,
                    "seconds": 30.0,
                },
                "log_path": str(log_dir / f"{run_id}_final_cook.jsonl"),
            },
            request_id=f"{run_id}-final-cook",
            policy=validate_policy,
            **common,
        ).as_dict()
    )
    metadata = {
        "skill": {"id": SKILL_ID, "version": SKILL_VERSION},
        "run_id": run_id,
        "spec": spec,
        "capability_input": {"mops_available": mops_available, "explicit": True},
        "recipes": [
            "sop.kinetic_reliquary_native@1.0.0",
            f"{overlay_recipe}@1.0.0",
            f"{presentation_recipe}@1.0.0",
            "lop.kinetic_reliquary_staged_stage@1.0.0",
        ],
        "render": {"requested": render_preview, "delegate": "BRAY_HdKarma", "resolution": [width, height], "frames": spec["sample_frames"], "outputs": [str(path) for path in render_paths.values()]},
        "selection": spec["selection"],
        "license": {"mode": "houdini-apprentice-noncommercial", "scene_extension": ".hipnc", "plugin_license": "LGPL-3.0"},
    }
    calls.extend(
        [
            build_envelope("graph.capture_svg", {"node_path": network_path, "output_path": str(obj_svg), "max_nodes": 96}, request_id=f"{run_id}-obj-svg", policy=validate_policy, **common).as_dict(),
            build_envelope("graph.capture_svg", {"node_path": "/stage", "output_path": str(lop_svg), "max_nodes": 32}, request_id=f"{run_id}-lop-svg", policy=validate_policy, **common).as_dict(),
            build_envelope("graph.capture_manifest", {"node_path": network_path, "output_path": str(graph_manifest), "metric_node_paths": [presentation_path], "metadata": metadata}, request_id=f"{run_id}-manifest", policy=validate_policy, **common).as_dict(),
            build_envelope("hip.save_snapshot", {"output_dir": str(scene_dir), "stem": f"kinetic_reliquary_{run_id}_final"}, request_id=f"{run_id}-snapshot", policy=validate_policy, **common).as_dict(),
        ]
    )
    return calls
