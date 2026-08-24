"""Rerender the validated Sprint 18 stage with crop-safe gallery framing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import hou
from hermes_houdini.dispatcher import Dispatcher
from hermes_houdini.policy import default_policy
from hermes_houdini.schemas.command import CommandEnvelope, Policy, RiskClass


def _dispatch(dispatcher: Dispatcher, envelope: CommandEnvelope):
    outcome = dispatcher.process_one(envelope)
    if outcome.result.status.value != "blocked":
        return outcome.result
    return dispatcher.process_one(
        CommandEnvelope(
            tool="approval.grant",
            request_id=f"{envelope.request_id}-grant",
            arguments={"approval_id": outcome.result.data["approval"]["approval_id"]},
        )
    ).result


def _require_success(results) -> None:
    failures = [result.errors for result in results if result.status.value != "success"]
    if failures:
        raise RuntimeError(f"Sprint 18 refinement failed: {failures}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True)
    parser.add_argument("--artifact-dir", required=True)
    arguments = parser.parse_args()
    scene = Path(arguments.scene).expanduser()
    artifact_dir = Path(arguments.artifact_dir).expanduser()
    if not scene.is_absolute() or not scene.is_file() or scene.suffix.lower() != ".hipnc":
        raise ValueError("--scene must be an existing absolute .hipnc path")
    if not artifact_dir.is_absolute():
        raise ValueError("--artifact-dir must be absolute")
    render = artifact_dir / "observations" / "sprint18_refined_karma_cpu.png"
    visual = artifact_dir / "manifests" / "sprint18_refined_visual_verification.json"
    critique = artifact_dir / "manifests" / "sprint18_refined_critique_packet.json"
    for path in (render, visual, critique):
        if path.exists():
            raise FileExistsError(f"refusing existing artifact: {path}")

    hou.hipFile.load(str(scene), suppress_save_prompt=True)
    dispatcher = Dispatcher(policy=default_policy([str(artifact_dir)]))
    common = {"session_id": "sprint18_refined", "project_id": "lookdev.procedural_material_foundry"}
    results = []
    for name, value in {
        "tx": 0.0,
        "ty": 2.6,
        "tz": 22.5,
        "rx": -3.5,
        "ry": 0.0,
        "rz": 0.0,
        "focalLength": 50.0,
    }.items():
        results.append(
            _dispatch(
                dispatcher,
                CommandEnvelope(
                    tool="node.set_parameter",
                    request_id=f"sprint18-refined-camera-{name}",
                    arguments={
                        "path": "/stage/SPRINT18_LIVE_CAMERA",
                        "name": name,
                        "value": value,
                    },
                    policy=Policy(risk=RiskClass.LOW, max_seconds=30),
                    **common,
                ),
            )
        )
    results.append(
        _dispatch(
            dispatcher,
            CommandEnvelope(
                tool="solaris.karma_rop.build",
                request_id="sprint18-refined-karma-rop",
                arguments={
                    "stage_node_path": "/stage/OUT_SPRINT18_LIVE_STAGE",
                    "render_settings_path": "/Render/SPRINT18_LIVE_Settings",
                    "output_path": str(render),
                    "checkpoint_dir": str(artifact_dir / "checkpoints"),
                    "log_path": str(artifact_dir / "logs" / "sprint18_refined_karma_rop.jsonl"),
                    "node_name": "SPRINT18_REFINED_KARMA_PREVIEW",
                    "width": 768,
                    "height": 432,
                    "frame": 1.0,
                    "time_limit": 90.0,
                    "max_threads": 4,
                },
                policy=Policy(
                    risk=RiskClass.MEDIUM,
                    max_seconds=90,
                    max_memory_bytes=1_073_741_824,
                    max_resolution=(768, 432),
                ),
                **common,
            ),
        )
    )
    results.append(
        _dispatch(
            dispatcher,
            CommandEnvelope(
                tool="render.karma.preview",
                request_id="sprint18-refined-karma-render",
                arguments={
                    "rop_path": "/out/SPRINT18_REFINED_KARMA_PREVIEW",
                    "output_path": str(render),
                    "log_path": str(artifact_dir / "logs" / "sprint18_refined_karma_render.jsonl"),
                    "frame": 1.0,
                },
                policy=Policy(
                    risk=RiskClass.EXTERNAL,
                    allow_external_process=True,
                    max_seconds=90,
                    max_memory_bytes=1_073_741_824,
                    max_frames=1,
                    max_output_bytes=536_870_912,
                    max_resolution=(768, 432),
                ),
                **common,
            ),
        )
    )
    _require_success(results)
    visual_result = _dispatch(
        dispatcher,
        CommandEnvelope(
            tool="visual.analyze",
            request_id="sprint18-refined-visual",
            arguments={"image_paths": [str(render)], "output_path": str(visual), "panel_count": 3},
            policy=Policy(risk=RiskClass.LOW, max_seconds=30, max_resolution=(768, 432)),
            **common,
        ),
    )
    _require_success([visual_result])
    critique_result = _dispatch(
        dispatcher,
        CommandEnvelope(
            tool="verification.critique.package",
            request_id="sprint18-refined-critique",
            arguments={
                "image_paths": [str(render)],
                "graph_path": str(artifact_dir / "observations" / "sprint18_live_lop_graph.svg"),
                "validation_paths": [
                    str(artifact_dir / "manifests" / "sprint18_live_pbr_channels.json"),
                    str(visual),
                ],
                "code_paths": [
                    str(Path(__file__).resolve()),
                    str(
                        Path(__file__).resolve().parents[1]
                        / "recipes"
                        / "lop"
                        / "procedural_material_foundry_stage.yaml"
                    ),
                ],
                "output_path": str(critique),
            },
            policy=Policy(risk=RiskClass.LOW, max_seconds=30),
            **common,
        ),
    )
    _require_success([critique_result])
    print(
        json.dumps(
            {
                "status": "success",
                "scene": str(scene),
                "render": str(render),
                "visual": json.loads(visual.read_text(encoding="utf-8")),
                "critique_packet": str(critique),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
