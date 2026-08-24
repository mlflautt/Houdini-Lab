"""Render a wider Sprint 17 before/after proof from its validated RBD snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import hou
from hermes_houdini.dispatcher import Dispatcher
from hermes_houdini.policy import default_policy
from hermes_houdini.schemas.command import CommandEnvelope, Policy, RiskClass
from hermes_houdini.skill_loader import load_skill


def _dispatch(dispatcher: Dispatcher, call: dict[str, object]):
    envelope = CommandEnvelope.from_dict(call)
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
        raise RuntimeError(f"refined render failed: {failures}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True)
    parser.add_argument("--artifact-dir", required=True)
    arguments = parser.parse_args()
    scene = Path(arguments.scene).expanduser()
    artifact_dir = Path(arguments.artifact_dir).expanduser()
    if not scene.is_absolute() or not scene.is_file():
        raise ValueError("--scene must be an existing absolute .hipnc path")
    if not artifact_dir.is_absolute():
        raise ValueError("--artifact-dir must be absolute")
    hou.hipFile.load(str(scene), suppress_save_prompt=True)
    hou.setFrame(48)
    source_path = "/obj/HERMES_RBD_SPRINT17_LIVE/OUT_SPRINT17_LIVE_COMPARE"
    if hou.node(source_path) is None:
        raise ValueError(f"validated RBD comparison source missing: {source_path}")

    dispatcher = Dispatcher(policy=default_policy([str(artifact_dir)]))
    skill = load_skill("skills/lookdev.relic_stage")
    calls = skill.plan(
        source_sop_path=source_path,
        artifact_dir=str(artifact_dir),
        run_id="sprint17_wide3",
        candidate_index=0,
        width=768,
        height=432,
        frame=48.0,
        time_limit=90.0,
        max_threads=4,
        render_preview=True,
    )
    results = [_dispatch(dispatcher, calls[0])]
    for name, value in {
        "tx": 24.0,
        "ty": 15.0,
        "tz": 29.0,
        "rx": -18.5,
        "ry": 39.0,
        "focalLength": 48.0,
    }.items():
        results.append(
            _dispatch(
                dispatcher,
                CommandEnvelope(
                    tool="node.set_parameter",
                    request_id=f"sprint17-wide-camera-{name}",
                    arguments={
                        "path": "/stage/SPRINT17_WIDE3_CAMERA",
                        "name": name,
                        "value": value,
                    },
                    policy=Policy(risk=RiskClass.LOW, max_seconds=30),
                ).as_dict(),
            )
        )
    results.extend(_dispatch(dispatcher, call) for call in calls[1:])
    _require_success(results)

    render = artifact_dir / "observations" / "sprint17_wide3_karma_cpu.png"
    visual = artifact_dir / "manifests" / "sprint17_wide3_visual_verification.json"
    visual_result = _dispatch(
        dispatcher,
        CommandEnvelope(
            tool="visual.analyze",
            request_id="sprint17-wide-visual",
            arguments={
                "image_paths": [str(render)],
                "output_path": str(visual),
                "panel_count": 2,
            },
            policy=Policy(risk=RiskClass.LOW, max_seconds=30, max_resolution=(768, 432)),
        ).as_dict(),
    )
    _require_success([visual_result])
    critique = artifact_dir / "manifests" / "sprint17_wide3_critique_packet.json"
    critique_result = _dispatch(
        dispatcher,
        CommandEnvelope(
            tool="verification.critique.package",
            request_id="sprint17-wide-critique",
            arguments={
                "image_paths": [str(render)],
                "graph_path": str(artifact_dir / "observations" / "sprint17_live_graph.svg"),
                "validation_paths": [
                    str(artifact_dir / "manifests" / "sprint17_live_rbd_validation.json"),
                    str(visual),
                ],
                "code_paths": [
                    str(Path(__file__).resolve()),
                    str(Path(__file__).resolve().parents[1] / "hermes_houdini" / "rbd.py"),
                ],
                "output_path": str(critique),
            },
            policy=Policy(risk=RiskClass.LOW, max_seconds=30),
        ).as_dict(),
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
